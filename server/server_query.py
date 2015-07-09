#!/usr/bin/python -O
import argparse
import os
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

import urllib2
import sqlite3
import time

os.chdir(os.path.dirname(os.path.realpath(__file__)))
conn = sqlite3.connect('../db/main.db')
db = {'conn': conn, 'c': conn.cursor()}

# this trick robbed from http://stackoverflow.com/questions/702834/whats-the-common-practice-for-enums-in-python
ID, CALLSIGN, DESCRIPTION, BASE_URL, LAST_SEEN, FIRST_SEEN, PINGS, DROPS, LATENCY, ACTIVE, LOG, NOTES = range(12)

parser = argparse.ArgumentParser()
parser.add_argument("-q", "--query", default="heartbeat", help="query to send to the servers (if heartbeat then this daemonizes)")
parser.add_argument("-c", "--callsign", default="all", help="station to query (default all)")
parser.add_argument('-l', '--list', action='store_true', help='show stations')
args = parser.parse_args()

# retrieve a list of the active stations
if args.callsign == 'all':
  station_list = db['c'].execute('select * from stations where active = 1')

else:
  station_list = db['c'].execute('select * from stations where active = 1 and callsign = "%s"' % args.callsign)

if args.list:
  for station in station_list.fetchall():
    print station[CALLSIGN]
  sys.exit(0)

for station in station_list.fetchall():
  url = station[BASE_URL]

  try:
    start = time.time()

    stream = urllib2.urlopen("http://%s/%s" % (url, args.query))
    data = stream.read()

    stop = time.time()

    print "---------\n%s\n%s" % (url, data)

    db['c'].execute('update stations set latency = latency + ?, pings = pings + 1, last_seen = current_timestamp where id = ?', ( str(stop - start), str(station[ID]) ))

  except urllib2.URLError:
    db['c'].execute('update stations set drops = drops + 1 where id = ?', str(station[ID]))

  except urllib2.HTTPError:
    # Say that we couldn't see this station
    db['c'].execute('update stations set drops = drops + 1 where id = ?', str(station[ID]))

if args.query == 'heartbeat':
  db['conn'].commit()

