#!/bin/bash
# Gets a remote stream (presuming you have the right credentials)
# based on a file name

stream=$1
station=$(echo $stream | sed 's/-.*//')

scp $station.indycast.net:radio/$station/streams/$stream .
