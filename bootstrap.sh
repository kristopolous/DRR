#!/bin/sh
cd server

sudo apt-get update

sudo apt-get -y -f install  \
    python-pip   python      \
    python-dev   libxslt1-dev \
    libxml2-dev  python-pycurl \
    sqlite3      zlib1g-dev 

pip install --user -r requirements.txt
