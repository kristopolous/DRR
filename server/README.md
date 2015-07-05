# Installation

You need the following things in debian based systems:
 
  sudo apt-get -y -f install  \
    python-pip   python       \
    python-dev   libxslt1-dev \
    libxml2-dev  python-pycurl 

Your OS of choice should have these in their own terms - remember
this is intended to be run on a server somewhere.

Then you need the requirements here. You can install them with

  pip install --user -r requirements.txt

