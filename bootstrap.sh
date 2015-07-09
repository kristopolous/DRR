#!/bin/sh
cd server

sudo apt-get update
sudo apt-get -y -f install    \
    python-pip   python       \
    python-dev   libxslt1-dev \
    libxml2-dev  python-pycurl 

pip install --user -r requirements.txt
