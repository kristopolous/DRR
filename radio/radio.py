#!/usr/bin/env python
import pycurl
import time
from multiprocessing import Process, Queue
from StringIO import StringIO
start_time = time.time()
round_ix = 0

def cback(data): 
  global round_ix, start_time

  round_ix += 1
  print str(float(round_ix) / (time.time() - start_time))

def dospawn(callsign, url):
  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

def spawner():
  q = Queue()
  stationMap = {
    'kpcc': {
      'url':'http://live.scpr.org/kpcclive/',
      'ts': time.time(),
      'process': False
    }
  }

  while not q.empty():
    q.get(False)
  
  for callsign,station in stationMap.items():
    if station['process'] == False:
      station['process'] = p = Process(target=dospawn, args=(callsign, station['url'],))
      p.start()
      p.join()
  
       
spawner()
