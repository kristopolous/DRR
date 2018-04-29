#!/bin/bash
# Gets a remote stream (presuming you have the right credentials)
# based on a file name

if [ $# -eq 0 ]; then
  echo "Usage: $0 station-time.mp3"
else
  while [ $# -gt 0 ]; do
    stream=`basename $1`
    station=$(echo $stream | sed 's/-.*//')

    if [ ! -z $stream ]; then 
      scp $station.indycast.net:radio/$station/streams/$stream . || ./cloud.py -g $stream
    fi

    shift
  done
fi
