#!/usr/bin/env python
import pycurl
import time
from multiprocessing import Process, Queue
from StringIO import StringIO
start_time = time.time()
round_ix = 0
q = Queue()

def dospawn(callsign, url):

  def cback(data): 
    global round_ix, start_time
    q.put(callsign)
    round_ix += 1
    print str(float(round_ix) / (time.time() - start_time))

  print "Spawning - " + callsign

  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

def spawner():
  global q
  stationMap = {
    'kpcc': {
      'url':'http://live.scpr.org/kpcclive/',
      'flag': False,
      'process': False
    }
  }

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
