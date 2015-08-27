#!/bin/sh
# Just miscellaneous garbage things
aac_unique() {
  set -x
  ./aac_parse_test.py > aac.hash 
  sort aac.hash > aac.hash.sorted 
  cat aac.hash.sorted | uniq -d -w 25 > dupes
  head -100 dupes > dupes.100
  grep -A 1 -B 1 -f dupes.100 aac.hash.sorted | less
}
