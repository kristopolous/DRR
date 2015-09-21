#!/usr/bin/python -O
#
# Tries to determine the schedule of a station
#
import urllib2
import json

active_stations_raw = urllib2.urlopen("http://indycast.net/api/stations").read()
active_station = json.loads(active_stations_raw)
