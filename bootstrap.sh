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
      python3                     \
      libcurl4-gnutls-dev       \
      libgnutls28-dev         

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

#aptinstall
pipinstall
# hardupgrade
pip3 install --user -r requirements.txt
