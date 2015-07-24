#!/bin/bash
#
# This rather sophisticated thing will take old files off the cloud that
# the servers do not know about.
#

# First we backup everything to get the databases

TMP_BASE="/tmp/list-"
backup_dir=~/backups/indycast/20150724-1447
#backup_dir=`./backup.sh 1`

# Go into the back up directory and expand all the stations
# in a subprocess
(
    cd $backup_dir

    # Parallelize this
    ls *gz | xargs -P 6 gunzip

    # I do not want to be told if there are errors here.
    # I really do not care that much.
) >& /dev/null

# Now for each station we take all the stream names
for station in `./server_query.py -n -l`; do

    echo -n "${station}: "

    # Gets the SQL list of files
    (
      cd $backup_dir

      [ -e ${TMP_BASE}db ] && rm ${TMP_BASE}db

      # Load the SQL dump into a temporary file
      sqlite3 ${TMP_BASE}db < $station

      echo -n "SQL "
      sqlite3 ${TMP_BASE}db 'select replace(name, "streams/", "") from streams' > ${TMP_BASE}sql
    )

    # Find all the files on the cloud for this station
    echo -n "Cloud "
    ./cloud.py -q list -s $station > ${TMP_BASE}cloud

    echo -n "SetDiff "
    # See what the difference of these two lists are
    cat ${TMP_BASE}cloud ${TMP_BASE}sql | sort | uniq -u > ${TMP_BASE}intersection

    # These would be the ones that appeared only once, and only in the cloud list.
    # This would be the thing we should dump.
    cat ${TMP_BASE}intersection ${TMP_BASE}cloud | sort | uniq -d > ${TMP_BASE}remove

    # We are going to make sure and confirm that there's nothing we are screwing up
    # before moving forward
    echo -n "Check1..."
    ./server_query.py -c $station -q stats > ${TMP_BASE}stats

    # If we take our remove list and use it as a grep list through the stats, the
    # wc -l of it should be zero
    overlap=`grep -f ${TMP_BASE}remove ${TMP_BASE}stats | wc -l`

    echo -n "$overlap "

    if [ "$overlap" -eq "0" ]; then
      echo "Pass"

      remove_count=`wc -l ${TMP_BASE}remove | awk ' { print $1 } '`
      cloud_count=`wc -l ${TMP_BASE}cloud | awk ' { print $1 } '`

      echo -n "${station}: About to remove $remove_count of $cloud_count files. Proceed [Y/(N)]? "
      read -i query

      if [ "$query" = "Y" ]; then
          echo "Very well then..."
          echo 'cat ${TMP_BASE}remove | ./cloud -q unlink'
      else
          echo "Aborting"
          exit -1
      fi

    else
      echo "Fail (Abort)"
      exit -1
    fi

    exit
done
