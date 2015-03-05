#!/usr/bin/env bash

# Stop on first error
set -e

# Disable the firewall to allow remote access
service iptables stop
chkconfig iptables off

# Update existing pkgs
yum -y update

# Desktop
yum -y groupinstall "Desktop" "Desktop Platform" "X Window System" "Fonts"

# VNC
yum -y install tigervnc-server

# Add the EPEL repo as a source (for Erlang)
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
rpm -Uvh epel-release-6*.rpm

# Erlang
yum -y install erlang

# Ruby client
gem install bunny

# Java
yum -y install java-1.8.0-openjdk-devel

# Add Ding-Yi Chen's Maven repo
# Stopped working 2015/3/5
# wget http://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo -O /etc/yum.repos.d/epel-apache-maven.repo
#sed -i s/\$releasever/6/g /etc/yum.repos.d/epel-apache-maven.repo
#sed -i s/\$basearch/x86_64/g /etc/yum.repos.d/epel-apache-maven.repo

# Maven
#yum -y install apache-maven

mkdir /opt
pushd /opt
wget http://mirror.gopotato.co.uk/apache/maven/maven-3/3.2.5/binaries/apache-maven-3.2.5-bin.zip
unzip apache-maven-3.2.5-bin.zip
popd 

# Eclipse
#yum -y install eclipse
pushd /opt
wget http://www.mirrorservice.org/sites/download.eclipse.org/eclipseMirror/technology/epp/downloads/release/luna/SR2/eclipse-java-luna-SR2-linux-gtk-x86_64.tar.gz
tar xvfz eclipse-java-luna-SR2-linux-gtk-x86_64.tar.gz
popd

# Git
yum -y install git

# Emacs
yum -y install emacs

# Firefox
yum -y install firefox
