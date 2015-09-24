#!/bin/bash
# 
# Restarts a single server through ssh under the following assumptions:
#
#   * The station exists 
#   * Is registered through indycast.net
#   * Public keys will work
#   * The server code is in DRR/server
#   

while [ $# -gt 0 ]; do
  station=$1
  ssh $station.indycast.net "cd DRR;git pull;./bootstrap.sh;cd server;pkill $station;./indy_server.py -c configs/$station.txt --daemon &" &
  shift
done
