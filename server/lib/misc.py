#!/usr/bin/python -O
import setproctitle as SP
import ConfigParser
import argparse
import os
import time
import requests
import re
import logging
import sys
import socket
__version__ = os.popen("git describe").read().strip()

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
import cloud
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
last_official_query = None

def do_nothing(signal, frame=None):
  """ Catches signals that we would rather just ignore """
  return True


def base_stats():
  """
  Reports base-level statistical information about the health of the server.
  This is used for the /stats and /heartbeat call.
  """
  return {
    'uptime': TS.uptime(),
    'last_recorded': float(DB.get('last_recorded', use_cache=False) or 0),
    'now': time.time(),
    'version': __version__,
    'load': [float(unit) for unit in os.popen("uptime | awk -F : ' { print $NF } '").read().split(', ')],
    'disk': cloud.size('.') / (1024.0 ** 3)
  }

def mail_config():
  cfg = os.environ.get('CLOUD_CFG')

  os.chdir(os.path.dirname(os.path.realpath(__file__)))

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
  args = parser.parse_args()

  if args.config is None:
    print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
    sys.exit(-1)

  cloud_config = ConfigParser.ConfigParser()
  cloud_config.read(args.config)

  return config_section_map('Mailgun', cloud_config)


# Taken from https://bradgignac.com/2014/05/12/sending-email-with-python-and-the-mailgun-api.html
def send_email(config, who, subject, body):
  key = config['base_key']
  request_url = "%s/%s" % (config['base_url'].strip('/'), 'messages')

  request = requests.post(request_url, auth=('api', key), data={
    'from': 'Indycast Reminders <reminders@indycast.net>',
    'to': who,
    'subject': subject,
    'text': re.sub('<[^<]+?>', '', body),
    'html': body
  })

  return request


def am_i_official():
  """ 
  Takes the callsign and port and queries the server for its per-instance uuid
  If those values match our uuid then we claim that we are the official instance
  and can do various privileged things.  Otherwise, we try not to intrude.
  """
  global config, last_official_query

  # Don't cache a true value ... see https://github.com/kristopolous/DRR/issues/84 for details
  # Actually we'll cache it for a few seconds.
  if 'official' not in config or (config['official'] and (not last_official_query or last_official_query + 10 < time.time())):
    endpoint = "http://%s.indycast.net:%d/uuid" % (config['callsign'], config['port'])

    try: 
      stream = urllib2.urlopen(endpoint)
      data = stream.read()
      config['official'] = (data.strip() == config['uuid'])
      last_official_query = time.time()

    except:
      # We can't contact the server so we just return false
      # and set nothing
      return False

  return config['official']


def public_config():
  """ Returns a configuration, removing sensitive information """
  global config 
  return {k: v for k, v in config.items() if k != '_private'}

def shutdown(signal=15, frame=None):
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


def manager_is_running(pid=None):
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
