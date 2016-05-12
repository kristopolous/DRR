#!/bin/bash
oldcfg=~/cloudcreds-old.cfg
newcfg=~/cloudcreds-new.cfg
done=list-done
remaining=list-remaining

fail() {
  echo "Failure, exiting here"
  exit
}

remaining() {
  touch $done
  cat list-all_old $done | sort | uniq -u > $remaining
}

remaining

while IFS='' read -r file || [[ -n "$file" ]]; do
  date

  ./cloud.py -c $oldcfg -g $file || fail
  ./cloud.py -c $newcfg -p $file || fail

  echo "Removing $file"
  rm $file
  echo $file >> $done
done < $remaining
