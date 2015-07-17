#!/usr/bin/python -O
import argparse
import os
import ConfigParser
import sys
import socket

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

from glob import glob
import urllib2
import sqlite3
import time
import random

os.chdir(os.path.dirname(os.path.realpath(__file__)))
conn = sqlite3.connect('../db/main.db')
db = {'conn': conn, 'c': conn.cursor()}

# this trick robbed from http://stackoverflow.com/questions/702834/whats-the-common-practice-for-enums-in-python
ID, CALLSIGN, DESCRIPTION, BASE_URL, LAST_SEEN, FIRST_SEEN, PINGS, DROPS, LATENCY, ACTIVE, LOG, NOTES = range(12)

parser = argparse.ArgumentParser()
parser.add_argument("-q", "--query", default="heartbeat", help="query to send to the servers (if heartbeat then this daemonizes)")
parser.add_argument("-c", "--callsign", default="all", help="station to query (default all)")
parser.add_argument('-l', '--list', action='store_true', help='show stations')
parser.add_argument('-n', '--notrandom', action='store_true', help='do not reandomize order')
args = parser.parse_args()

# retrieve a list of the active stations
if args.callsign == 'all':
  station_list = db['c'].execute('select * from stations where active = 1')

else:
  station_list = db['c'].execute('select * from stations where active = 1 and callsign = "%s"' % args.callsign)

all_stations = station_list.fetchall()

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
  url = station[BASE_URL]
  hasFailure = False

  try:
    start = time.time()

    # Take out the \n (we'll be putting it in below)
    sys.stdout.write("%s " % url)

    stream = urllib2.urlopen("http://%s/%s" % (url, args.query), timeout = 15)
    data = stream.read()

    stop = time.time()

    print "[ %d ]\n%s" % (stop - start, data)

    db['c'].execute('update stations set active = 1, latency = latency + ?, pings = pings + 1, last_seen = current_timestamp where id = ?', ( str(stop - start), str(station[ID]) ))

  except Exception as e:
    hasFailure = str(e)

  # If this wasn't hit that means that we weren't able to access the host for
  # one reason or another.
  if hasFailure:
    # Stop the timer and register it as a drop.
    stop = time.time()
    print "[ %d ] Failure: %s\n" % (stop - start, hasFailure)
    db['c'].execute('update stations set drops = drops + 1 where id = ?', str(station[ID]))

if args.query == 'heartbeat':
  db['conn'].commit()

