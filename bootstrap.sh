#!/bin/sh
#
# Intended for Jessie (Debian 8)
#
cd server

aptinstall() {
  #sudo apt-get update

  sudo apt-get -y -f install  \
      python-pip   python      \
      python-dev   libxslt1-dev \
      libxml2-dev  python-pycurl \
      sqlite3      zlib1g-dev     \
      uuid-runtime build-essential \
      python3-pip  python3        \
      libcurl4-gnutls-dev       \
      libgnutls28-dev         
}

hardupgrade() {
  rm -r build
  yes | sudo pip3 uninstall azure 
}

aptinstall
# hardupgrade
/usr/bin/pip-3 install --user -r requirements.txt
