#!/bin/bash
station=$1

ssh $station.indycast.net "cd DRR/server;pkill $station;./indy_server.py -c configs/$station.txt --daemon &" &
