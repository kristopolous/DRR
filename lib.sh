#!/bin/bash

showname=`basename $0`
arg=$1
length=$(( arg * 3645 ))

cmd() {
  file="/home/chris/alien/$showname-`date +%c`.mp3"
  audio
  pid=$!
}
cmd

for (( i = 0; i < $length; i++ )); do
  lc=`ps h --pid $pid | wc -l`
  [ $lc -eq 0 ] && cmd
  sleep 1
done

kill $pid
