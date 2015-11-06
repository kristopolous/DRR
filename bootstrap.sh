#!/bin/sh
cd server

aptinstall() {
  sudo apt-get update

  sudo apt-get -y -f install  \
      python-pip   python      \
      python-dev   libxslt1-dev \
      libxml2-dev  python-pycurl \
      sqlite3      zlib1g-dev     \
      uuid-runtime build-essential
}

hardupgrade() {
  rm -r build
  yes | sudo pip uninstall azure 
}

aptinstall
# hardupgrade
pip install --user -r requirements.txt
