#!/usr/bin/env python
import pycurl
import time
import ConfigParser
from flask import Flask
import sys
from multiprocessing import Process, Queue
from StringIO import StringIO
start_time = time.time()
round_ix = 0
q = Queue()
storage_dir = "/var/radio/"

def server():
    app = Flask(__name__)

    @app.route('/heartbeat')
    def heartbeat():
        return "hi" + request.remote_addr

    
    @app.route('/<weekday>/<start>/<duration>/<name>')
    def stream(weekday, start, duration, name):
        return weekday + start + duration + name
    

    app.run()

def dospawn(callsign, url):

  def cback(data): 
    global round_ix, storage_dir, start_time
    q.put(callsign)
    round_ix += 1
    stream.write(data)
    print str(float(round_ix) / (time.time() - start_time))

  print "Spawning - " + callsign

  try:
      stream = open(storage_dir + callsign + "-" + str(int(time.time())) + ".mp3", 'w')
  except:
      print "Unable to open " + storage_dir + ". Maybe sudo mkdir it?"
      sys.exit(-1)

  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

  stream.close()

def spawner():
  global q
  stationMap = {
    'kpcc': {
      'url':'http://live.scpr.org/kpcclive/',
      'flag': False,
      'process': False
    }
  }

  server_pid = Process(target=server)
  server_pid.start()

  while True:
    
    while not q.empty():
      callsign = q.get(False)
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
  
       
spawner()
