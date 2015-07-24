#!/usr/bin/python -O
import argparse
import os
import re
import ConfigParser
import sys
import socket
import lib.misc as misc

#
# This is needed to force ipv4 on ipv6 devices. It's sometimes needed
# if there isn't a clean ipv6 route to get to the big wild internet.
# In these cases, a pure ipv6 route simply will not work.  People aren't
# always in full control of every hop ... so it's much safer to force
# ipv4 then optimistically cross our fingers.
#
origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)

# Replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2
import sqlite3
import time
import random
from glob import glob

os.chdir(os.path.dirname(os.path.realpath(__file__)))
try:
  conn = sqlite3.connect('../db/main.db')
  db = {'conn': conn, 'c': conn.cursor()}
  # this trick robbed from http://stackoverflow.com/questions/702834/whats-the-common-practice-for-enums-in-python
  ID, CALLSIGN, DESCRIPTION, BASE_URL, LAST_SEEN, FIRST_SEEN, PINGS, DROPS, LATENCY, ACTIVE, LOG, NOTES = range(12)

except:
  db = False
  CALLSIGN = 'callsign'


parser = argparse.ArgumentParser()
parser.add_argument("-q", "--query", default="heartbeat", help="query to send to the servers (if heartbeat then this daemonizes)")
parser.add_argument("-c", "--callsign", default="all", help="station to query (default all)")
parser.add_argument('-l', '--list', action='store_true', help='show stations')
parser.add_argument('-n', '--notrandom', action='store_true', help='do not reandomize order')
args = parser.parse_args()

config_list = []
if not db:
  for station_config in glob('../server/configs/*txt'):
    Config = ConfigParser.ConfigParser()
    Config.read(station_config)
    config = misc.config_section_map('Main', Config)
    config_list.append(config)

# retrieve a list of the active stations
if args.callsign == 'all':
  if db:
    station_list = db['c'].execute('select * from stations where active = 1')
    all_stations = station_list.fetchall()
  else:
    all_stations = config_list

else:
  if db:
    station_list = db['c'].execute('select * from stations where active = 1 and callsign in ("%s")' % re.sub(',', '","', args.callsign)) 
    all_stations = station_list.fetchall()
  else:
    all_stations = []
    callsign_list = args.callsign.split(',')

    for config in config_list:
      if config['callsign'] in callsign_list:
        all_stations.append(config)

if args.list:
  # Just list all the supported stations
  for station in all_stations:
    print station[CALLSIGN]

  sys.exit(0)

# From https://github.com/kristopolous/DRR/issues/19:
# shuffling can allow for more robust querying if something locks up - 
# although of course a lock up should never happen. ;-)
if not args.notrandom:
  random.shuffle(all_stations)

for station in all_stations:
  if db:
    url = station[BASE_URL]
  else:
    url = "%s.indycast.net:%s" % (station[CALLSIGN], station['port'])

  hasFailure = False

  try:
    start = time.time()

    # If we are just looking at one station, then we may want to 
    # look at this data as JSON, so we suppress any superfluous output
    if len(all_stations) > 1:
      # Take out the \n (we'll be putting it in below)
      sys.stdout.write("%s " % url)

    stream = urllib2.urlopen("http://%s/%s" % (url, args.query), timeout=15)
    data = stream.read()

    stop = time.time()

    if len(all_stations) == 1:
      sys.stdout.write(data)
       
    else:
      print "[ %d ]\n%s" % (stop - start, data)

    if db:
      db['c'].execute('update stations set active = 1, latency = latency + ?, pings = pings + 1, last_seen = current_timestamp where callsign = ?', ( str(stop - start), str(station[CALLSIGN]) ))

  except Exception as e:
    hasFailure = str(e)

  # If this wasn't hit that means that we weren't able to access the host for
  # one reason or another.
  if hasFailure:
    # Stop the timer and register it as a drop.
    stop = time.time()
    print "[ %d ] Failure: %s\n" % (stop - start, hasFailure)

    if db:
      db['c'].execute('update stations set drops = drops + 1 where id = ?', str(station[ID]))

if args.query == 'heartbeat' and db:
  db['conn'].commit()

