#!/usr/bin/python -O
import argparse
import os
import re
import ConfigParser
import sys
import socket
import lib.misc as misc
import json

#
# This is needed to force ipv4 on ipv6 devices. It's sometimes needed
# if there isn't a clean ipv6 route to get to the big wild internet.
# In these cases, a pure ipv6 route simply will not work.  People aren't
# always in full control of every hop ... so it's much safer to force
# ipv4 then optimistically cross our fingers.
#
origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  attempts = 1
  max_attempts = 10

  while attempts < max_attempts:
    try:
      res = origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)
      return res

    except:
      print "[%d/%d] Unable to resolve %s on %d ... sleeping a bit" % (attempts, max_attempts, host, port)
      time.sleep(1)
      attempts += 1

  # If we have tried this a few times and nothing happens, then we just bail
  raise Exception

# Replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2
import sqlite3
import time
import random
from glob import glob

CALLSIGN = 'callsign'
os.chdir(os.path.dirname(os.path.realpath(__file__)))
try:
  conn = sqlite3.connect('../db/main.db')
  db = {'conn': conn, 'c': conn.cursor()}
  # this trick robbed from http://stackoverflow.com/questions/702834/whats-the-common-practice-for-enums-in-python

except:
  db = False


parser = argparse.ArgumentParser()
parser.add_argument("-q", "--query", default=None, help="query to send to the servers (if heartbeat then this daemonizes)")
parser.add_argument("-c", "--callsign", default="all", help="station to query (default all)")
parser.add_argument('-l', '--list', action='store_true', help='show stations')
parser.add_argument('-k', '--key', default=None, help='Get a specific key in a json formatted result')
parser.add_argument('-n', '--notrandom', action='store_true', help='do not reandomize order')
args = parser.parse_args()

config_list = []

# This permits just an inquiry like server_query -c kcrw -k version
if not args.query:
  args.query = "stats" if args.key else "heartbeat"

for station_config in glob('../server/configs/*txt'):
  Config = ConfigParser.ConfigParser()
  Config.read(station_config)
  config = misc.config_section_map('Main', Config)
  config_list.append(config)

# retrieve a list of the active stations
if args.callsign == 'all':
  all_stations = config_list

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
  url = "%s.indycast.net:%s" % (station[CALLSIGN], station['port'])

  hasFailure = False

  try:
    start = time.time()

    # If we are just looking at one station, then we may want to 
    # look at this data as JSON, so we suppress any superfluous output
    if len(all_stations) > 1:
      # Take out the \n (we'll be putting it in below)
      sys.stderr.write("%s " % url)

    stream = urllib2.urlopen("http://%s/%s" % (url, args.query), timeout=15)
    data = stream.read()

    if args.key:
      document = json.loads(data)
      result_list = []

      full_key_list = args.key.split(',')

      for full_key in full_key_list:
        key_parts = full_key.split('.')

        my_node = document
        for key in key_parts:

          if key in my_node:
            my_node = my_node[key]

          else:
            my_node = '<Invalid key>'

        result_list.append({full_key: my_node})

      data = json.dumps(result_list)

    stop = time.time()

    if len(all_stations) == 1:
      sys.stdout.write(data)
       
    else:
      sys.stderr.write("[ %d ]\n" % (stop - start))
      print data

    if db:
      db['c'].execute('update stations set active = 1, latency = latency + ?, pings = pings + 1, last_seen = current_timestamp where callsign = ?', ( str(stop - start), str(station[CALLSIGN]) ))

  except Exception as e:
    hasFailure = str(e)

  # If this wasn't hit that means that we weren't able to access the host for
  # one reason or another.
  if hasFailure:
    # Stop the timer and register it as a drop.
    stop = time.time()
    print "[ %d:%s ] Failure: %s\n" % (stop - start, url, hasFailure)

    if db:
      db['c'].execute('update stations set drops = drops + 1 where callsign = "%s"' % station[CALLSIGN] )

if args.query == 'heartbeat' and db:
  db['conn'].commit()

