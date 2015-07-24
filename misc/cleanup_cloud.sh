#!/bin/bash
#
# This rather sophisticated thing will take old files off the cloud that
# the servers do not know about.
#

# This is the basename and path that we use in order to
# store all of our files.  This process isn't very space 
# intensive but we do need a few files.  It's better to
# name them consistently and make sure that we know where
# they all are for debugging.
TMP_BASE="/tmp/list-"

# First we backup everything to get the databases

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
for station in `./server_query.py -l`; do

    echo -n "${station}: "

    # Gets the SQL list of files by going into the 
    # backup directory and loading the sql dump into
    # a temporary database that we query on and then
    # send the output to a temporary file
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
    cloud_count=`wc -l ${TMP_BASE}cloud | awk ' { print $1 } '`

    echo -n "SetDiff "
    # See what the difference of these two lists are
    cat ${TMP_BASE}cloud ${TMP_BASE}sql | sort | uniq -u > ${TMP_BASE}intersection

    # These would be the ones that appeared only once, and only in the cloud list.
    # This would be the thing we should dump.
    cat ${TMP_BASE}intersection ${TMP_BASE}cloud | sort | uniq -d > ${TMP_BASE}remove
    remove_count=`wc -l ${TMP_BASE}remove | awk ' { print $1 } '`

    if [ "$remove_count" -eq "0" ]; then
      echo "[ Nothing to remove ]"
      continue
    fi

    # We are going to make sure and confirm that there's nothing we are screwing up
    # before moving forward
    echo -n "Checking..."
    ./server_query.py -c $station -q stats > ${TMP_BASE}stats

    # If we take our remove list and use it as a grep list through the stats, the
    # wc -l of it should be zero
    overlap=`grep -f ${TMP_BASE}remove ${TMP_BASE}stats | wc -l`

    echo -n "$overlap "

    if [ "$overlap" -eq "0" ]; then
      echo "Pass"

      # Now we manually prompt the user because this is a pretty irreversible little thing we
      # are about to do.
      #
      # Just to make sure, we're going to tell the user how many files we'd like to remove
      # and then place it with respect to the total number of files for that station.  The
      # user can then decide whether this sounds like a reasonably sane number of things
      # to delete or whether it looks like there may be some bug somewhere.
      #
      echo -n "${station}: About to remove $remove_count of $cloud_count files. Proceed [y/(n)]? "
      read -e query

      if [ "$query" = "y" ]; then
          echo "Very well then..."
          cat ${TMP_BASE}remove | ./cloud.py -q unlink
      else
          echo "Aborting"
          exit -1
      fi

    else
      echo "Fail (Abort)"
      exit -1
    fi

done
