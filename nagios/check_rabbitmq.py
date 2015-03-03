#!/usr/bin/python
#
# Nagios check_mk script returning one line per RabbitMQ resource:
#     (Node, Connection, Channel, Exchange) - TBD
#     Queue

from __future__ import print_function # for print-to-stderr
from datetime import datetime, timedelta
import json
import os
import sys
from time import clock, mktime, sleep, time

# Additional opts (fix to obtain from conf)
VHOST = '%2F'

WAIT_TIME_WARN = 60
WAIT_TIME_CRIT = 180

STATUS = ['OK', 'WARN', 'CRIT']



# Uses the rabbitmqadmin script.
# To be imported this must be given a .py suffix and placed in the current dir or 
# on the Python path

import sys
from ConfigParser import ConfigParser, NoSectionError
from optparse import OptionParser, TitledHelpFormatter
import httplib
import urllib
import urlparse
import base64
import json
import os
import socket

options=          { "hostname"        : "localhost",
                    "port"            : "15672",
                    "amqp_port"       : "5672",
                    "declare_vhost"   : "/",
                    "username"        : "guest",
                    "password"        : "guest",
                    "ssl"             : False,
                    "verbose"         : True,
                    "format"          : "table",
                    "depth"           : 1,
                    "bash_completion" : False }

class Management:
    def __init__(self, options):
        self.options = options

    def get(self, path):
        return self.http("GET", "/api%s" % path, "")

    def http(self, method, path, body):
        if self.options["ssl"]:
            conn = httplib.HTTPSConnection(self.options["hostname"],
                                           self.options["port"],
                                           self.options["ssl_key_file"],
                                           self.options["ssl_cert_file"])
        else:
            conn = httplib.HTTPConnection(self.options["hostname"],
                                          self.options["port"])
        headers = {"Authorization":
                       "Basic " + base64.b64encode(self.options["username"] + ":" +
                                                   self.options["password"])}
        if body != "":
            headers["Content-Type"] = "application/json"
        try:
            conn.request(method, path, body, headers)
        except socket.error, e:
            die("Could not connect: {0}".format(e))
        resp = conn.getresponse()
        if resp.status == 400:
            die(json.loads(resp.read())['reason'])
        if resp.status == 401:
            die("Access refused: {0}".format(path))
        if resp.status == 404:
            die("Not found: {0}".format(path))
        if resp.status == 301:
            url = urlparse.urlparse(resp.getheader('location'))
            [host, port] = url.netloc.split(':')
            self.options["hostname"] = host
            self.options["port"] = int(port)
            return self.http(method, url.path + '?' + url.query, body)
        if resp.status < 200 or resp.status > 400:
            raise Exception("Received %d %s for path %s\n%s"
                            % (resp.status, resp.reason, path, resp.read()))
        return resp.read()

# TIMEOUT_SECS = 10

UNDEFINED = 'undefined'

def log(*args):
    return
    print("\nINFO: ", *args, file=sys.stderr)

def out(checkline):
    print(checkline)

def get_queue_stats():
    stats_str = mgmt.get('/queues/' + VHOST + '/')
    log(json.loads(stats_str))
    return json.loads(stats_str)


"""
Metrics are values derived from Rabbit stats that may be checked against thresholds and passed to Check MK as Performance Data
"""
class metric_base(object):
    def __init__(self, value, warn = None, crit = None):
        self.v = value
        self.warn = warn
        self.crit = crit

    def check_thresholds(self):
        if self.v == None: return 0
        if self.warn != None and self.v <= self.warn: return 0
        if self.crit != None and self.v <= self.crit: return 1
        if self.crit != None and self.v > self.crit: return 2
        return 0

    def get_label(self):
        return type(self).__name__[:-7]

    def check(self, all_services):
        return self.check_thresholds()

    """
    Return value formatted for service "check output" (descriptive) field
    """
    def to_description(self):
        if self.v != None:
            return str(self.v)
        else:
            return 'no value'
    
    """
    Return name, value and limits formatted for performance data field
    """
    def to_perf_data(self):
        pdlist = []
        if self.v != None:
            pdlist.append(self.v)
        else:
            pdlist.append('-') # Unknown/missing perf data is indicated by dash
        if self.warn != None:
            pdlist.append(self.warn)
        if self.crit != None:
            pdlist.append(self.crit)
        return self.get_label() + "=" + ''.join(str(pd) + ';' for pd in pdlist)[:-1]

class consumers_metric(metric_base):
    pass

class msgs_metric(metric_base):
    pass

class rate_in_metric(metric_base):
    pass

class rate_out_metric(metric_base):
    pass

class unacked_metric(metric_base):
    pass

class wait_time_metric(metric_base):
    def to_description(self):
        if self != None:
           return str(timedelta(seconds=self.v))
        else:
           return self.super()

"""
A Nagios service, e.g. a Rabbit queue
"""
class service_base(object):
    def __init__(self, name):
        self.name = name
        self.status = None
        self.metrics = {}
        self.problem_metric = None
        self.problem_metric_status = 0

    def check(self, all_services):
        problem_metric = None
        problem_metric_status = 0
        for key in sorted(self.metrics.keys()):
            metric = self.metrics[key]
            status = metric.check(all_services)
            if status > problem_metric_status: # Allow more severe status to replace less
                problem_metric = key
                problem_metric_status = status
        self.problem_metric = problem_metric
        self.status = problem_metric_status
        
    """
    Status description for the Check Output field
    """
    def output(self):
        return self.normal_output() if self.status == 0 else self.problem_output()

    def normal_output(self):
        return 'OK'

    def problem_output(self):
        return '{0} - {1} is {2}'.format(STATUS[self.status], self.problem_metric, self.metrics[self.problem_metric].to_description())

    def format_perf_data(self):
        return ''.join(self.metrics[key].to_perf_data() + '|' for key in sorted(self.metrics.keys()))[:-1]

    def format_checkline(self):
        return "{0} {1} {2} {3}".format(self.status, self.name, self.format_perf_data(), self.output())


class queue_service(service_base):

    """
    Create queue service given the management stats for a single queue
    """
    def __init__(self, qs):
        super(queue_service, self).__init__('RMQ_' + qs['node'].split('@')[0] + '_Q_' + qs['name'])
        bqs = qs.get('backing_queue_status')
        self.metrics['wait_time'] = wait_time_metric(
            None if qs.get('backing_queue_status').get('head_msg_timestamp') in [UNDEFINED, None] else (time() - qs['backing_queue_status']['head_msg_timestamp']),
            WAIT_TIME_WARN,
            WAIT_TIME_CRIT)
        self.metrics['rate_in'] = rate_in_metric(bqs.get('avg_ingress_rate'))
        self.metrics['rate_out'] = rate_out_metric(bqs.get('avg_egress_rate'))
        self.metrics['consumers'] = consumers_metric(qs.get('consumers'))
        self.metrics['msgs'] = msgs_metric(bqs.get('len'))
        self.metrics['unacked'] = unacked_metric(qs.get('messages_unacknowledged'))

    def normal_output(self):
        # TODO consumers don't show in basic_get s = 'consumers {0}'.format(self.metrics['consumers'].to_description())
        s = 'OK - '
        if (self.metrics['msgs'].v != None) and (self.metrics['msgs'].v > 0): s+= 'msgs {0}'.format(self.metrics['msgs'].to_description())
        if (self.metrics['wait_time'].v != None): s+= ', wait time {0}'.format(self.metrics['wait_time'].to_description())
        return s

def main():
    global mgmt
    mgmt = Management(options)
    services = []
    services += [queue_service(queue_stats) for queue_stats in get_queue_stats()]
    for service in services:
        service.check(services)
    checklines = ''.join([service.format_checkline() + '\n' for service in services])
    out(checklines)

if __name__ == '__main__':
     main()
    
