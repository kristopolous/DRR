#!/usr/bin/python -O
import setproctitle as SP
import ConfigParser
import os
import time
import logging
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
  attempts = 1
  max_attempts = 10

  while attempts < max_attempts:
    try:
      res = origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)
      return res

    except:
      print "[%d/%d] Unable to resolve %s on %d ... sleeping a bit" % (attempts, max_attempts, host, port)
      time.sleep(1)
      attempts += 1

  # If we have tried this a few times and nothing happens, then we just bail
  raise Exception


# Replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2
import urllib

import ts as TS
import db as DB
from multiprocessing import Process, Queue, Lock

#
# The process delay is used throughout to measure things like the delay in
# forking a subprocesses, waiting for DNS, and then starting a stream or
# waiting for all the sub-processes like the web-server to clean up and free
# the tcp port they are listening on, and shut down.  
#
# Making this generous shouldn't be discouraged as it is also used as a metric
# to calculate the number of accomodations that are to be given to make service
# continuous.
#
# Things are specified in multiples of this value ... for instance PROCESS_DELAY
# / 4 or * 2.  4 is a good number.
#
PROCESS_DELAY = 4

#
# Maintain a pidfile for the manager and the webserver (which
# likes to become a zombie ... braaaainnns!) so we have to take
# care of it separately and specially - like a little retard.
#
PIDFILE_MANAGER = 'pid-manager'
PIDFILE_WEBSERVER = 'pid-webserver'

DIR_BACKUPS = 'backups'
DIR_STREAMS = 'streams'
DIR_SLICES = 'slices'

IS_TEST = True

manager_pid = 0
queue = Queue()

start_time = None
config = {}
pid = {}
lockMap = {'prune': Lock()}

def donothing(signal, frame=False):
  """ Catches signals that we would rather just ignore """
  return True


def am_i_official():
  """ 
  Takes the callsign and port and queries the server for its per-instance uuid
  If those values match our uuid then we claim that we are the official instance
  and can do various privileged things.  Otherwise, we try not to intrude.
  """
  global config

  # Don't cache a true value ... see https://github.com/kristopolous/DRR/issues/84 for details
  if 'official' not in config or config['official']:
    endpoint = "http://%s.indycast.net:%d/uuid" % (config['callsign'], config['port'])
    try: 
      stream = urllib2.urlopen(endpoint)
      data = stream.read()
      config['official'] = (data.strip() == config['uuid'])

    except:
      # We can't contact the server so we just return false
      # and set nothing
      return False

  return config['official']


def public_config():
  """ Returns a configuration, removing sensitive information """
  global config 
  return {k: v for k, v in config.items() if k != '_private'}

def shutdown(signal=15, frame=False):
  """ Shutdown is hit on the keyboard interrupt """
  global queue, start_time, config

  # Try to manually shutdown the webserver
  if os.path.isfile(PIDFILE_WEBSERVER):
    with open(PIDFILE_WEBSERVER, 'r') as f:
      webserver = f.readline()

      try:  
        os.kill(int(webserver), signal)

      except:
        pass

    try:  
      os.unlink(PIDFILE_WEBSERVER)

    except:
      pass

  title = SP.getproctitle()

  print "[%s:%d] Shutting down" % (title, os.getpid())

  DB.shutdown()

  logging.info("[%s:%d] Shutting down through signal %d" % (title, os.getpid(), signal))

  if title == ('%s-manager' % config['callsign']):
    global pid
    for key, value in pid.items():
      try:
        value.terminate()
      except:
        pass

    logging.info("Uptime: %ds", TS.uptime())

  elif title != ('%s-webserver' % config['callsign']) and os.path.isfile(PIDFILE_MANAGER):
    os.unlink(PIDFILE_MANAGER)

  queue.put(('shutdown', True))
  sys.exit(0)


def manager_is_running(pid=False):
  """
  Checks to see if the manager is still running or if we should 
  shutdown.  It works by sending a signal(0) to a pid and seeing
  if that fails.

  Returns True/False
  """
  global manager_pid

  if pid:
    manager_pid = pid
    return pid

  try:
    os.kill(manager_pid, 0)
    return True

  except:
    return False

  
def change_proc_name(what):
  """
  Sets a more human-readable process name for the various 
  parts of the system to be viewed in top/htop.
  """
  SP.setproctitle(what)
  print "[%s:%d] Starting" % (what, os.getpid())
  return os.getpid()


# From https://wiki.python.org/moin/ConfigParserExamples
def config_section_map(section, Config):
  """
  Takes a section in a config file and makes a dictionary
  out of it.

  Returns that dictionary.
  """
  dict1 = {}
  options = Config.options(section)

  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
        logging.info("skip: %s" % option)

    except Exception as exc:
      logging.warning("exception on %s!" % option)
      dict1[option] = None

  return dict1  
