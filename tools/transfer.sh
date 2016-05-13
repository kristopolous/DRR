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
  cat list-all_old $done | sort | uniq -u > $remaining-unsorted
  cat $remaining-unsorted | awk -F \- ' { print $2" "$0 } ' | sort -n | awk ' { print $2 } ' > $remaining
}

remaining

n=0
list=""
while IFS='' read -r file || [[ -n "$file" ]]; do
  (( n++ ))

  if [ $n = 8 ]; then
    date

    ./cloud.py -c $oldcfg -g $list || fail
    ./cloud.py -c $newcfg -p $list || fail

    # Note that this is removing the old file only
    # after the new one has been placd in the cloud
    ./cloud.py -c $oldcfg -d $list || fail

    echo $list | tr ',' ' ' | xargs rm
    echo $list | tr ',' '\n' >> $done

    n=0
    list=""
  fi

  if [ -z "$list" ]; then
    list=$file
  else
    list="$list,$file"
  fi
done < $remaining
