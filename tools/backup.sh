#!/bin/bash
#
# Downloads gzipped sqlite3 databases from all the stations
# specified in the configuration directory (from server-query)
#
# If an argument is supplied then it just echos the backup directory
# This is useful for scripting this in larger infrastructures
#

scripted=$#

# Make a base file name
fname_base=`date +"%Y%m%d-%H%M"`

# Decide on a directory
backup_dir=~/backups/indycast/$fname_base
[ -e $backup_dir ] || mkdir -p $backup_dir

# First we list all of the stations
for station in `./server_query.py -n -l`; do

  [ $scripted ] || echo -n "Backing up $station ... "

  ./server_query.py -q db -c $station > $backup_dir/$station.gz

  [ $scripted ] || echo `du -b $backup_dir/$station.gz | awk ' { print $1 } '`

done

[ $scripted ] && echo $backup_dir || du -k $backup_dir
