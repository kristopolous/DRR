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
getAddrInfoWrapper = misc.getAddrInfoWrapper
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
parser.add_argument("-q", "--query", default=None, help="query to send to the servers (site-map gives all end points)")
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

station_count = len(all_stations)
station_ix = 0

if args.key and station_count > 1:
  print '['

for station in all_stations:
  station_ix += 1
  url = "%s.indycast.net:%s" % (station[CALLSIGN], station['port'])

  hasFailure = False

  try:
    start = time.time()

    # If we are just looking at one station, then we may want to 
    # look at this data as JSON, so we suppress any superfluous output
    if len(all_stations) > 1 and not args.key:
      # Take out the \n (we'll be putting it in below)
      sys.stderr.write("%s " % url)

    stream = urllib2.urlopen("http://%s/%s" % (url, args.query), timeout=15)
    data = stream.read()
    stop = time.time()

    if args.query == 'heartbeat':
      document = json.loads(data)
      document['delta'] = document['now'] - float(document['last_recorded'])
      data = json.dumps(document, indent=2)

    if args.key:
      document = json.loads(data)
      result_map = {}

      full_key_list = args.key.split(',')

      for full_key in full_key_list:
        # This makes it so that things like key[1].hello become key.1].hello
        key_parts = re.sub('\[', '.', full_key).strip('.').split('.')

        my_node = document
        for key in key_parts:
          try:
            # This takes care of the closing brace left above
            key_numeric = int(key.strip(']'))
            
          except:
            pass

          if key in my_node:
            my_node = my_node[key]

          elif type(my_node) is list and type(key_numeric) is int and key_numeric < len(my_node):
            my_node = my_node[key_numeric]

          else:
            my_node = '<Invalid key>'

        result_map[full_key] = my_node

      result_map['url'] = url
      result_map['latency'] = stop - start

      data = json.dumps(result_map)

      if station_ix < station_count:
        data += ','

    if len(all_stations) == 1:
      sys.stdout.write(data)
       
    else:
      if not args.key:
        sys.stderr.write("[ %d ]\n" % (stop - start))

      print data

    if db and args.query == 'heartbeat':
      db['c'].execute('''
        update stations set 
          active = 1, 
          log = ?, 
          latency = latency + ?, 
          pings = pings + 1, 
          last_seen = current_timestamp 
        where callsign = ?''', ( str(document['delta']), str(stop - start), str(station[CALLSIGN]) ))

  except Exception as e:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    hasFailure = str(e)

  # If this wasn't hit that means that we weren't able to access the host for
  # one reason or another.
  if hasFailure:
    # Stop the timer and register it as a drop.
    stop = time.time()
    print "[ %d:%s ] Failure(@%d): %s\n" % (stop - start, url, exc_traceback.tb_lineno, hasFailure)

    if db:
      db['c'].execute('update stations set drops = drops + 1 where callsign = "%s"' % station[CALLSIGN] )

if args.query == 'heartbeat' and db:
  db['conn'].commit()

if args.key and station_count > 1:
  sys.stdout.write(']')

