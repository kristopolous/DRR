#!/usr/bin/python -O
import setproctitle as SP
import ConfigParser
import os
import time
import logging
import sys
import lib.db as DB
from multiprocessing import Process, Queue, Lock

#
# Maintain a pidfile for the manager and the webserver (which
# likes to become a zombie ... braaaainnns!) so we have to take
# care of it separately and specially - like a little retard.
#
PIDFILE_MANAGER = 'pid-manager'
PIDFILE_WEBSERVER = 'pid-webserver'

manager_pid = 0
queue = Queue()

start_time = time.time()
config = {}
pid = {}
lockMap = {'prune': Lock()}

def kill(who):
  global queue
  queue.put(('terminate', who))

def set_config(config_in):
  global config
  config = config_in

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

    logging.info("Uptime: %ds", time.time() - start_time)

  elif title != ('%s-webserver' % config['callsign']) and os.path.isfile(PIDFILE_MANAGER):
    os.unlink(PIDFILE_MANAGER)

  queue.put(('shutdown', True))
  sys.exit(0)


def manager_is_running(pid=False):
  """
  Checks to see if the manager is still running or if we should 
  shutdown.  It works by sending a signal(0) to a pid and seeing
  if that fails
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
  parts of the system to be viewed in top/htop
  """
  SP.setproctitle(what)
  print "[%s:%d] Starting" % (what, os.getpid())
  return os.getpid()

# From https://wiki.python.org/moin/ConfigParserExamples
def config_section_map(section, Config):
  """
  Takes a section in a config file and makes a dictionary
  out of it.

  Returns that dictionary
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
