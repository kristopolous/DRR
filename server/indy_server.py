#!/usr/bin/env python
import argparse
import ConfigParser
import json
import logging
import os
import pycurl
import shutil
import sqlite3
import sys
import time
import socket

origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)

# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2

from datetime import datetime
from flask import Flask, request, jsonify
from multiprocessing import Process, Queue
from StringIO import StringIO

g_start_time = time.time()
g_round_ix = 0
g_queue = Queue()
g_config = {}
g_last = {}
g_db = False

"""
schema

  start minute (1 - 10080) on a weekly basis starting 1 minute after 11:59PM sunday
  end minute 
  created_at
  accessed_at

"""

def now():
  ts = datetime.datetime.utcnow()
  return ts.weekday() * (24 * 60 * 60) + ts.utcnow().hour * 60 + ts.utcnow().minute

def db_connect():
  global g_db

  conn = sqlite3.connect('config.db')
  g_db = {'conn': conn, 'c': conn.cursor()}

  g_db.c.execute("create table if not exist intents(start integer, end integer, created_at timestamp default current_timestamp, accessed_at timestamp default current_timestamp)");
  g_db.conn.commit()


def register_intent(minute, duration):
  return True
  
def should_be_recording():
  return True
  
def prune():
  global g_config

  duration = int(g_config['archivedays']) * 60 * 60 * 24
  cutoff = time.time() - duration

  count = 0
  for f in os.listdir(g_config['storage']): 
    entry = g_config['storage'] + f
  
    if os.path.isfile(entry) and os.path.getctime(entry) < cutoff:
      print "Prune: %s" % (entry)
      os.unlink(entry)
      count += 1 

  print "Found %d files older than %s days." % (count, g_config['archivedays'])

def get_time_offset():
  global g_config
  when = int(time.time())

  api_key='AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
  url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%d&key=%s" % (g_config['lat'], g_config['long'], when, api_key)
 
  f = urllib2.urlopen(url)
  myfile = f.read()
  opts = json.loads(myfile)

  if opts['status'] == 'OK': 
    g_config['offset'] = int(opts['rawOffset']) / 60
    return True

    # Let's do something at least
  else:
    g_config['offset'] = 0

  return False

def server():
  app = Flask(__name__)

  @app.route('/heartbeat')
  def heartbeat():
    global g_config

    if request.remote_addr != '127.0.0.1':
      return '', 403

    stats = {
      'disk': sum(os.path.getsize(g_config['storage'] + f) for f in os.listdir(g_config['storage']) if os.path.isfile(g_config['storage'] + f))
    }

    return jsonify(stats), 200
  
  @app.route('/<weekday>/<start>/<duration>/<name>')
  def stream(weekday, start, duration, name):
    register_intent(to_utc(weekday, start), duration)
    return weekday + start + duration + name

  app.run(debug=True)

def download(callsign, url):

  def cback(data): 
    global g_round_ix, g_config, g_start_time

    g_queue.put(True)
    g_round_ix += 1
    stream.write(data)
    print str(float(g_round_ix) / (time.time() - g_start_time))

  print "Spawning - " + callsign

  try:
    stream = open(g_config['storage'] + callsign + "-" + str(int(time.time())) + ".mp3", 'w')
  except:
    print "Unable to open " + g_config['storage'] + ". Maybe sudo mkdir it?"
    sys.exit(-1)

  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

  stream.close()

def ago(duration):
  return time.time() - duration

# This takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
# and a 12 hour time hh:mm [ap]m and converts it to our absolute units
# with respect to the timestamp in the configuration file
def to_utc(day_str, hour):
  global g_config

  try:
    day_number = ['sun','mon','tue','wed','thu','fri','sat','sun'].index(day_str.lower())
  except e:
    return False

  time_re = re.compile('(\d{1,2}):(\d{2})([ap])m')

  time = time_re.findall(hour)

  if len(time) == 0:
    return False

  local = day_number * (60 * 60 * 24);
  local += int(time[0]) * 60
  local += int(time[1])

  if time[2] == 'p':
    local += (12 * 60)

  utc = local + g_config['offset']

  return utc

def spawner():
  global g_queue, g_config, g_last

  station = {
    'callsign': g_config['callsign'],
    'url': g_config['stream'],
    'flag': False,
    'process': False
  }

  g_last = {
    'prune': 0,
    'offset': 0
  }

  minute = 60
  hour = 60 * minute
  day = 24 * hour
  b_shutdown = False

  server_pid = Process(target=server)
  server_pid.start()

  while True:

    if g_last['prune'] < ago(1 * day):
      prune()
      g_last['prune'] = time.time()

    if g_last['offset'] < ago(1 * day):
      get_time_offset()
      g_last['offset'] = time.time()

    while not g_queue.empty():
      b = g_queue.get(False)

      if b == 'shutdown':
        b_shutdown = True
      else:
        station['flag'] = True
    
    # didn't respond in 3 seconds so we respawn
    if station['flag'] == False:
      if station['process'] != False and station['process'].is_alive():
        station['process'].terminate()
      station['process'] = False

    if station['process'] == False and b_shutdown == False:
      station['process'] = p = Process(target=download, args=(g_config['callsign'], station['url'],))
      p.start()

    # If there is still no process then we should definitely bail.
    if station['process'] == False:
      return False

    station['flag'] = False

    time.sleep(3)

# From https://wiki.python.org/moin/ConfigParserExamples
def ConfigSectionMap(section, Config):
  dict1 = {}
  options = Config.options(section)

  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
        DebugPrint("skip: %s" % option)

    except:
      print("exception on %s!" % option)
      dict1[option] = None

  return dict1  

def startup():
  global g_config, g_conn

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
  parser.add_argument("-v", "--version", help="Version info")
  args = parser.parse_args()

  Config = ConfigParser.ConfigParser()
  Config.read(args.config)
  g_config = ConfigSectionMap('Main', Config)

  if os.path.isdir(g_config['storage']):
    os.chdir(g_config['storage'])
  else:
    logging.warning("Can't find %s. Using current directory" % g_config['storage'])

  db_connect()

  get_time_offset()
  sys.exit(0)

def shutdown():
  global g_db, g_queue
  g_db.c.commit()
  g_db.conn.close()
  g_queue.put('shutdown')

startup()      
spawner()
