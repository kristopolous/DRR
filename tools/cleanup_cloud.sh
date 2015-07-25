#!/bin/bash
#
# This rather sophisticated thing will take old files off the cloud that
# the servers do not know about.
#
# Without arguments it will go through all the stations. 
#
# An optional argument would be a quoted string of stations
# to use.
# 
# In fact, here is where that's determined.
#
station_list=${1:-`./server_query.py -l | shuf`}

#
# This is the basename and path that we use in order to
# store all of our files.  This process isn't very space 
# intensive but we do need a few files.  It's better to
# name them consistently and make sure that we know where
# they all are for debugging.
#
TMP_BASE="/tmp/list-"

script_dir=`pwd`

#
# First we backup everything to get the databases.
#
# This creates a corresponding database dump on each server
# which gets removed in the config['archivedays'] number of days.
#
# Although these files are small, it's probably best not to run
# this process flippantly.  
#

if [ -z "$DOWNLOAD" ]; then
  # The most recent backup can be found by just doing this:
  echo "Using most recent backup. Start like $ DOWNLOAD=1 ./cleanup_cloud.sh to force"
  backup_dir=~/backups/indycast/`ls -1t ~/backups/indycast | head -1`
else
  echo "Running backup on all hosts to get database list..."
  backup_dir=`./backup.sh 1`
fi


# Now for each station we take all the stream names.
for station in $station_list; do

  echo -n "${station} - "

  #
  # Gets the SQL list of files by going into the 
  # backup directory and loading the sql dump into
  # a temporary database that we query on and then
  # send the output to a temporary file.
  #
  db_path=$backup_dir/${station}.gz

  if [ ! -e $db_path ]; then
    echo "Unable to find DB for $station in $db_path ... I can't do anything here"
    continue
  fi

  # Load the SQL dump into a temporary file
  [ -e ${TMP_BASE}db ] && rm ${TMP_BASE}db
  zcat $db_path | sqlite3 ${TMP_BASE}db 

  echo -n "SQL:"
  sqlite3 ${TMP_BASE}db 'select replace(name, "streams/", "") from streams' > ${TMP_BASE}sql
  sql_count=`cat ${TMP_BASE}sql | wc -l`
  echo -n $sql_count

  if [ $sql_count -lt 10 ]; then
    echo "Found under 10 entries ... we will assume this is an error."
    continue
  fi

  # Find all the files on the cloud for this station.
  echo -n " Cloud:"
  ./cloud.py -q list -s $station > ${TMP_BASE}cloud
  if [ $? -ne "0" ]; then
    echo "The script exited unexpectedly. Bailing"
    exit 1
  fi

  cloud_count=`cat ${TMP_BASE}cloud | wc -l`
  echo -n "$cloud_count SetDiff:"
  if [ "$cloud_count" -lt "5" ]; then
    echo "The cloud count is under 5, which sounds fishy. So we'll skip this."
    continue
  fi

  # See what the difference of these two lists are.
  cat ${TMP_BASE}cloud ${TMP_BASE}sql | sort | uniq -u > ${TMP_BASE}intersection

  # These would be the ones that appeared only once, and only in the cloud list.
  # This would be the thing we should dump.
  cat ${TMP_BASE}intersection ${TMP_BASE}cloud | sort | uniq -d > ${TMP_BASE}remove
  remove_count=`cat ${TMP_BASE}remove | wc -l`
  echo -n $remove_count

  if [ "$remove_count" -eq "0" ]; then
    echo "...Nothing to remove."
    continue
  fi

  # We are going to make sure and confirm that there's nothing we are screwing up
  # before moving forward.
  echo -n " Checking..."
  ./server_query.py -c $station -q stats > ${TMP_BASE}stats
  if [ $? -ne "0" ]; then
    echo "The script exited unexpectedly. Bailing"
    exit 1
  fi
  exists=`cat ${TMP_BASE}stats | wc -l`

  echo -n "$exists:"
  if [ $exists -lt 10 ]; then
    echo "Unable to get a reliable stats number ... bailing on this station"
    continue
  fi

  # If we take our remove list and use it as a grep list through the stats, the
  # wc -l of it should be zero.
  overlap=`grep -f ${TMP_BASE}remove ${TMP_BASE}stats | wc -l`

  echo -n "$overlap "

  if [ "$overlap" -eq "0" ]; then
    echo "Pass"

    #
    # Now we manually prompt the user because this is a pretty irreversible little thing we
    # are about to do.
    #
    # Just to make sure, we're going to tell the user how many files we'd like to remove
    # and then place it with respect to the total number of files for that station.  The
    # user can then decide whether this sounds like a reasonably sane number of things
    # to delete or whether it looks like there may be some bug somewhere.
    #

    # If it's a small number of things to remove, then just print the list to stdout
    if [ $remove_count -lt "5" ]; then
      echo "${station} - Remove list:"
      cat ${TMP_BASE}remove 
    fi

    while [ 0 ]; do
      echo -n "${station} - About to remove $remove_count of $cloud_count files. Proceed [(y)es / (l)ist / (s)kip / (a)bort]? "
      read query

      if [ "$query" = "y" ]; then
        echo "${station} - Very well then...removing."
        cat ${TMP_BASE}remove | ./cloud.py -q unlink
        break

      elif [ "$query" = "s" ]; then
        echo "Skipping..."
        break

      elif [ "$query" = "l" ]; then
        echo "${station} - Remove list:"
        cat ${TMP_BASE}remove 

      else
        echo "Aborting"
        exit -1
      fi

    done

  else
    echo "Fail (Abort)"
    exit -1
  fi

done
