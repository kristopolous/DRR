#!/bin/bash

# Decide on a directory
backup_dir=~/backups/indycast
[ -e $backup_dir ] || mkdir -p $backup_dir

# Make a base file name
fname_base=`date +"%Y%m%d-%H%M"`

# First we list all of the stations
for station in `./server_query.py -n -l`; do
  echo "Backing up $station"
  ./server_query.py -q db -c $station > $backup_dir/$station-$fname_base.gz
done
