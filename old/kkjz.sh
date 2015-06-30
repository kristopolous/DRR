#!/bin/bash

audio() {
  mplayer -dumpfile "$file" -dumpstream 'http://1.ice1.firststreaming.com:80/kkjz_fm.aac?type=.mp3' <  /dev/null &
}

. lib.sh
