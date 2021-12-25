#!/bin/sh
#
# Intended for Jessie (Debian 8)
# Should also work in Ubuntu 14.04 and 16.04
#

aptinstall() {
  sudo apt-get update

  for package in python3-dev python3-pip libxslt1-dev libxml2-dev python3-pycurl sqlite3 zlib1g-dev uuid-runtime build-essential python3 libcurl4-gnutls-dev libgnutls28-dev ; do
    sudo apt-get -y -f install $package
  done
}

pipinstall()  {
  sudo apt-get -y -f install python3-pip
}

hardupgrade() {
  rm -r build
  yes | sudo pip3 uninstall azure 
}

dopip() {
  cd server
  pip3=`which pip3`
  [ -e /usr/bin/pip-3.2 ] && pip3=/usr/bin/pip-3.2
  [ -e /usr/bin/pip-3.4 ] && pip3=/usr/bin/pip-3.4
  $pip3 install --upgrade --user -r requirements.txt
}

#aptinstall
pipinstall
# hardupgrade
dopip
