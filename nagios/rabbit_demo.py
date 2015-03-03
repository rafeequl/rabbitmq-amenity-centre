#!/usr/bin/python
#
# Init and control script for demo - run as python -i 
# Requires pika (pip install pika)

from datetime import datetime
import json
import pika
import os
import sys
from threading import Thread
from time import clock, mktime, sleep
import unittest

# Uses the rabbitmqadmin script.
# To be imported this must be given a .py suffix and placed on the Python path
from rabbitmqadmin import *

fruits = ['apples', 'pears', 'bananas' ]
markets = ['camden', 'hoxton', 'spitalfields' ]

logpath = "rabbit_demo.log"

pubs = {}
subs = {}

AMQP_PORT = 5672 # Not available from rabbitmqadmin config

TIMEOUT_SECS = 10

TIMESTAMP1 = mktime(datetime(2010,1,1,12,00,01).timetuple())
TIMESTAMP2 = mktime(datetime(2010,1,1,12,00,02).timetuple())

parser.set_conflict_handler('resolve')
(options, args) = make_configuration() 
mgmt = Management(options, args)

credentials = pika.PlainCredentials(options.username, options.password)
parameters =  pika.ConnectionParameters(options.hostname, port=int(5672), credentials=credentials)

logfile = open(logpath, "w+")

def log(msg):
    print >> logfile, msg

def create_exch(exch):
    mgmt.put('/exchanges/%2f/' + exch, '{"type" : "fanout", "durable":true}')

def delete_exch(exch):
    mgmt.delete('/exchanges/%2f/' + exch)

def create_queue(queue, exch):
    mgmt.put('/queues/%2f/' + queue, '{"auto_delete":false,"durable":true,"arguments":[]}') 
    mgmt.post('/bindings/%2f/e/' + exch + '/q/' + queue, '{"routing_key": ".*", "arguments":[]}')

def delete_queue(queue):
    mgmt.delete('/queues/%2f/' + queue)

def get_queue_stats(queue):
    stats_str = mgmt.get('/queues/%2f/' + queue)
    return json.loads(stats_str)

def get_exchs():
    stats_str = mgmt.get('/exchanges/%2f')
    return json.loads(stats_str)

def get_queues():
    stats_str = mgmt.get('/queues/%2f')
    return json.loads(stats_str)

def get_head_msg_timestamp(queue):
    return get_queue_stats(queue)["backing_queue_status"]["head_msg_timestamp"]

def send(channel, exch, message, timestamp=None):
    channel.basic_publish(exch, '', message,
                               pika.BasicProperties(content_type='text/plain',
                                                    delivery_mode=2,
                                                    timestamp=mktime(datetime.now().timetuple())))
    log("Sent message to exch " + exch + " with body: " + str(message))

def receive(channel, queue):
    method_frame, header_frame, body = channel.basic_get(queue = queue)
    if method_frame != None:
        log("Received message from queue " + queue + " with body: " + str(body))
        return method_frame.delivery_tag, body
    else:
        return None, None

def ack(channel, delivery_tag):
    channel.basic_ack(delivery_tag)        

def nack(channel, delivery_tag):
    channel.basic_nack(delivery_tag)        

def wait_for_new_timestamp(queue, old_timestamp):
    stats_wait_start = clock()
    while ((clock() - stats_wait_start) < TIMEOUT_SECS and
           get_head_msg_timestamp(queue) == old_timestamp):
        sleep(0.1)
    log('Queue stats updated in ' + str(clock() - stats_wait_start) + ' secs.')
    return get_head_msg_timestamp(queue)


class Pub(Thread):

    def __init__(self, exch):
        super(Pub, self).__init__()
        self.exch = exch
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.pausetime = 5.0
        self.active = True
        self.msgnum = 1

    def run(self):
        while(True):
            if active:
                send(self.channel, self.exch, "Message number " + str(self.msgnum) + " on exch " + self.exch)
                self.msgnum = self.msgnum + 1
            sleep(self.pausetime) 

class Sub(Thread):

    def __init__(self, queue):
        super(Sub, self).__init__()
        self.queue = queue
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.pausetime = 5.0
        self.active = True
        self.acking = True

    def run(self):
        while(True):
            if active:
                tag, body = receive(self.channel, self.queue)
                if tag != None:
                    if self.acking:
                        ack(self.channel, tag)
                    else:
                        nack(self.channel, tag)
            sleep(self.pausetime) 

def init():
    for fruit in fruits:
        create_exch(fruit)
        for market in markets:
            create_queue(fruit + "." + market, fruit)

def cleanup():
    for queue in get_queues():
        name = queue["name"]
        delete_queue(name)
    for exch in get_exchs():
        name = exch["name"]
        if ("amq" not in name) and (name != ""):
            delete_exch(name)

def create_pubs():
    for fruit in fruits:
        pubs[fruit] = Pub(fruit)

def create_subs():
    for fruit in fruits:
        for market in markets:
            subs[fruit + "." + market] = Sub(fruit + "." + market)

def create():
    create_pubs()
    create_subs()

def start_pubs():
    for pub in pubs.keys():
        pubs[pub].start()

def start_subs():
    for sub in subs.keys():
        subs[sub].start()
    
def start():
    start_pubs()
    start_subs()

def stop_pubs():
    for pub in pubs.keys():
        pubs[pub].active = False

def stop_subs():
    for sub in subs.keys():
        subs[sub].active = False

def stop():
    stop_pubs()
    stop_subs()
