#!/bin/sh

curl -s indycast.net/ | \
  grep http | awk -F \/ ' { print $4"."$3 } ' | \
  xargs -n 1 host | awk ' { print $NF" "$1 } ' | \
  sort
