#!/bin/bash
# 
# This is similar to the android adb logcat functionality.
# It ssh ins to the server and tail -f's its log. It works
# dependent on
#
#   * The station exists 
#   * Is registered through indycast.net
#   * Public keys will work
#   * The server code is in DRR/server
#   
station=$1

ssh $station.indycast.net "cd radio/$station;tail -f indycast.log"
