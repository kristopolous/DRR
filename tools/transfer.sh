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

n=0
list=""
while IFS='' read -r file || [[ -n "$file" ]]; do
  (( n++ ))

  if [ $n = 8 ]; then
    date

    ./cloud.py -c $oldcfg -g $list || fail
    ./cloud.py -c $newcfg -p $list || fail

    echo $list | tr ',' ' ' | xargs rm
    echo $list | tr ',' '\n' >> $done

    n=0
    list=""
  else
    if [ -z "$list" ]; then
      list=$file
    else
      list="$list,$file"
    fi
  fi
done < $remaining
