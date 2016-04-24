#!/bin/bash
#
# Downloads gzipped sqlite3 databases from all the stations
# specified in the configuration directory (from server-query)
#
# If an argument is supplied then it just echos the backup directory
# This is useful for scripting this in larger infrastructures
#

if [ $# -eq 0 ]; then
  station_list=`./server_query.py -l `
else
  station_list=$*
fi

# Make a base file name
fname_base=`date +"%Y%m%d-%H%M"`

# Decide on a directory
backup_dir=~/backups/indycast/$fname_base
[ -e $backup_dir ] || mkdir -p $backup_dir

for station in $station_list; do

  ./server_query.py -q db -s $station > $backup_dir/$station.gz
done

echo $backup_dir 
