#!/bin/bash

# Make a base file name
fname_base=`date +"%Y%m%d-%H%M"`

# Decide on a directory
backup_dir=~/backups/indycast/$fname_base
[ -e $backup_dir ] || mkdir -p $backup_dir

# First we list all of the stations
for station in `./server_query.py -n -l`; do
  echo -n "Backing up $station ... "
  ./server_query.py -q db -c $station > $backup_dir/$station.gz
  echo `du -b $backup_dir/$station.gz | awk ' { print $1 } '`
done
du -k $backup_dir
