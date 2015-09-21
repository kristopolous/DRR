#!/usr/bin/python -O
#
# Tries to determine the schedule of a station
#
import urllib2
import json
import pycurl

def url_get(url):
  curl_handle = pycurl.Curl()
  curl_handle.setopt(curl_handle.URL, url)
  curl_handle.setopt(pycurl.WRITEFUNCTION, cback)
  curl_handle.setopt(pycurl.FOLLOWLOCATION, True)

  try:
    curl_handle.perform()

  except Exception as exc:
    logging.warning("Couldn't resolve or connect to %s. %s" % (url, exc))

  curl_handle.close()

active_station_raw = urllib2.urlopen("http://indycast.net/api/stations").read()
active_station_list = json.loads(active_station_raw)
tuple_set = [(s['website'], s['callsign']) for s in active_station_list]
print tuple_set
