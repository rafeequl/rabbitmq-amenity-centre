#!/usr/bin/env bash

# Stop on first error
set -e

# Disable the firewall to allow remote access
service iptables stop
chkconfig iptables off

# Add the EPEL repo as a source (for Erlang)
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
rpm -Uvh epel-release-6*.rpm

# Erlang
yum -y install erlang

# RabbitMQ config
echo '[{rabbit, [{loopback_users, []}]}].' > /etc/rabbitmq/rabbitmq.config 



