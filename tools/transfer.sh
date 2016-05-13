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
  touch fail-list
  grep mp3 fail-list > fail-list.files
  cat fail-list.files list-all_old $done | sort | uniq -u > $remaining-unsorted
  cat $remaining-unsorted | awk -F \- ' { print $2" "$0 } ' | sort -n | awk ' { print $2 } ' > $remaining
}

remaining

n=0
list=""
let "limit = $RANDOM % 3 + 2"
while IFS='' read -r file || [[ -n "$file" ]]; do
  (( n++ ))

  if [ $n = 8 ]; then
    echo -e "\n-- "`date`" --"

    ./cloud.py -c $oldcfg -g $list 2>> fail-list
    get=$?

    if [ "$get" -eq "0" ]; then
      ./cloud.py -c $newcfg -p $list 2>> fail-list
      put=$?

      if [ "$put" -eq "0" ]; then
        # Note that this is removing the old file only
        # after the new one has been (succesfully) placd in the cloud
        ./cloud.py -c $oldcfg -d $list || fail

        echo $list | tr ',' '\n' >> $done
      else
        echo -e "\n\n ... skipping ... \n"
      fi
    else
      echo -e "\n\n ... skipping ... \n"
    fi
    # We remove the local copies regardless
    echo $list | tr ',' ' ' | xargs rm -f

    n=0
    list=""
    let "limit = $RANDOM % 3 + 2"
  fi

  if [ -z "$list" ]; then
    list=$file
  else
    list="$list,$file"
  fi
done < $remaining
