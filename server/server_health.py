#!/usr/bin/python -O
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

g_db = {}

def db_connect():
  """
  a "singleton pattern" or some other fancy $10-world style of maintaining 
  the database connection throughout the execution of the script.

  Returns the database instance
  """

  global g_db

  if 'conn' not in g_db:
    conn = sqlite3.connect('../db/main.db')
    g_db = {'conn': conn, 'c': conn.cursor()}

  return g_db

db = db_connect()

cycle_time = 60 * 60 * 12

# this trick robbed from http://stackoverflow.com/questions/702834/whats-the-common-practice-for-enums-in-python
ID, CALLSIGN, DESCRIPTION, BASE_URL, LAST_SEEN, FIRST_SEEN, PINGS, DROPS, LATENCY, ACTIVE, LOG, NOTES = range(12)

while True:
  # retrieve a list of the active stations
  station_list = db['c'].execute('select * from stations where active == 1')

  for station in station_list:
    url = station[BASE_URL]
    try:
      stream = urllib2.urlopen("http://%s/stats" % url)

    except urllib2.HTTPError:
      # Say that we couldn't see this station
      db['c'].execute('update stations set drops = drops + 1 where id = ?', str(station[ID]))
      db['conn'].commit()

    data = stream.read()
    print data

  time.sleep(cycle_time)
