#!/bin/sh
#
# Intended for Jessie (Debian 8)
# Should also work in Ubuntu 14.04 and 16.04
#

aptinstall() {
  sudo apt-get update

  for package in python-dev libxslt1-dev libxml2-dev python-pycurl sqlite3 zlib1g-dev uuid-runtime build-essential python3 libcurl4-gnutls-dev libgnutls28-dev ; do
    sudo apt-get -y -f install $package
  done
}

pipinstall()  {
  sudo apt-get -y -f install python3-pip
  # see http://askubuntu.com/questions/412178/how-to-install-pip-for-python-3-in-ubuntu-12-04-lts
  if [ $? -ne 0 ]; then
    sudo apt-get -y -f install python3-setuptools
    sudo easy_install3 pip
  fi
}

hardupgrade() {
  rm -r build
  yes | sudo pip3 uninstall azure 
}

dopip() {
  cd server
  pip3=`which pip3`
  [ -e /usr/bin/pip-3.2 ] && pip3=/usr/bin/pip-3.2
  $pip3 install --upgrade --user -r requirements.txt
}

aptinstall
pipinstall
# hardupgrade
dopip
