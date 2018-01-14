#!/bin/bash
PATH=/usr/local/bin:/usr/bin:$PATH
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/../server
config=configs/$1.txt
prog=./indy_server.py
if [ ! -e $config ]; then
  echo $config not found
  exit -1
fi

if [ ! -e $prog ]; then
  echo $prog not found
  exit -1
fi

while [ 0 ]; do
  cd $DIR/../server
  $prog -c $config
  # we need to make sure that there isn't some crazy loop
  sleep 1
done

