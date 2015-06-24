#!/usr/bin/env python
import argparse
import ConfigParser
import os
import pycurl
import shutil
import sqlite3
import sys
import time

from flask import Flask, request, jsonify
from multiprocessing import Process, Queue
from StringIO import StringIO

g_start_time = time.time()
g_round_ix = 0
g_queue = Queue()
g_config = {}

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
        return weekday + start + duration + name

    app.run(debug=True)

def dospawn(callsign, url):

  def cback(data): 
    global g_round_ix, g_config, g_start_time

    g_queue.put(callsign)
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

def spawner():
  global g_queue, g_config

  stationMap = {}
  stationMap[g_config['callsign']] = {
    'url': g_config['stream'],
    'flag': False,
    'process': False
  }

  server_pid = Process(target=server)
  server_pid.start()

  while True:
    
    while not g_queue.empty():
      callsign = g_queue.get(False)
      stationMap[callsign]['flag'] = True
    
    for callsign,station in stationMap.items():
      # didn't respond in 3 seconds so we respawn
      if station['flag'] == False:
        if station['process'] != False and station['process'].is_alive():
          station['process'].terminate()
        station['process'] = False

      if station['process'] == False:
        station['process'] = p = Process(target=dospawn, args=(callsign, station['url'],))
        p.start()

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
  global g_config

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
  parser.add_argument("-v", "--version", help="Version info")
  args = parser.parse_args()

  Config = ConfigParser.ConfigParser()
  Config.read(args.config)
  g_config = ConfigSectionMap('Main', Config)

startup()      
spawner()
