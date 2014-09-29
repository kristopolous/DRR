#!/bin/bash

n=$1
showname=kpcc
length=$(( n * 3645 ))
file="/home/chris/alien/$showname-`date +%c`.mp3"

curl http://live.scpr.org/kpcclive/ > "$file" &
mplayer=$!
sleep $length
kill $!
