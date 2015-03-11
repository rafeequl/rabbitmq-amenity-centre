#!/usr/bin/env bash

# Stop on first error
set -e

# Disable the firewall to allow remote access
service iptables stop
chkconfig iptables off

# Add the EPEL repo as a source (for Erlang)
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
rpm -Uvh epel-release-6*.rpm
sed -i "s/mirrorlist=https/mirrorlist=http/" /etc/yum.repos.d/epel.repo


# Erlang
yum -y install erlang

# RabbitMQ Server
rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
yum -y install https://www.rabbitmq.com/releases/rabbitmq-server/v3.4.4/rabbitmq-server-3.4.4-1.noarch.rpm
chkconfig rabbitmq-server on
# Create an initial config which allows guest to login remotely (disabled by default)
echo '[{rabbit, [{loopback_users, []}]}].' > /etc/rabbitmq/rabbitmq.config 
service rabbitmq-server start
rabbitmq-plugins enable rabbitmq_management


