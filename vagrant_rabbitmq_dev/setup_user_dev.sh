#!/usr/bin/env bash

# Stop on first error
set -e

echo '
export PATH=~/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-1.8.0
' | cat .bashrc - > .bashrc.new


# Links to non-repo pkgs
mkdir ~/bin

ln -s /opt/apache-maven-3.2.5/mvn ~/bin/mvn

ln -s /opt/eclipse/eclipse ~/bin/eclipse


