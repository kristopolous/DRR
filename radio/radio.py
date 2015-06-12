#!/usr/bin/env python
import pycurl
import time
from multiprocessing import Process, Queue
from StringIO import StringIO
start_time = time.time()
round_ix = 0

def spawner():

def dospawn(callsign, url):
  c = pycurl.Curl()
  c.setopt(c.URL, 'http://live.scpr.org/kpcclive/')
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

def cback(data): 
  global round_ix, start_time

  round_ix += 1
  print str(float(round_ix) / (time.time() - start_time))
       

