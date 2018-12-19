#!/usr/bin/python3
import setproctitle as SP
import configparser
import os
import time
import requests
import re
import logging
import sys
import socket
import signal
import threading
import resource, psutil
__version__ = os.popen("/usr/bin/git describe").read().strip()
source_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

#
# This is needed to force ipv4 on ipv6 devices. It's sometimes needed
# if there isn't a clean ipv6 route to get to the big wild internet.
# In these cases, a pure ipv6 route simply will not work.  People aren't
# always in full control of every hop ... so it's much safer to force
# ipv4 then optimistically cross our fingers.
#
origGetAddrInfo = socket.getaddrinfo
prune_duration = 0

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  attempts = 1
  max_attempts = 10

  while attempts < max_attempts:
    try:
      res = origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)
      return res

    except:
      logging.warn( "[%d/%d] Unable to resolve %s on %d ... sleeping a bit" % (attempts, max_attempts, host, port))
      time.sleep(1)
      attempts += 1

  # If we have tried this a few times and nothing happens, then we just bail
  raise Exception


# Replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

from urllib.request import urlopen

import lib.ts as TS
import lib.db as DB
import lib.cloud as cloud
from queue import Queue
from threading import Lock

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

DIR_BACKUPS = 'backups'
DIR_STREAMS = 'streams'
DIR_SLICES = 'slices'

IS_TEST = True

manager_pid = 0
queue = Queue()

params = {'shutdown_time': None}
start_time = None
config = {}
lockMap = {'prune': Lock(), 'main': Lock()}
last_official_query = None

def do_nothing(signal, frame=None):
  # Catches signals that we would rather just ignore 
  return True


def base_stats():
  # Reports base-level statistical information about the health of the server.
  # This is used for the /stats and /heartbeat call.
  try:
    # for some reason this can lead to a memory error
    load = [float(unit) for unit in os.popen("/usr/bin/uptime | awk -F : ' { print $NF } '").read().split(', ')]

  except:
    load = 0

  uptime = TS.uptime()
  return {
    'human-uptime': "%dd %02d:%02d:%02d" % ( uptime / TS.ONE_DAY_SECOND, (uptime / TS.ONE_HOUR_SECOND) % 24, (uptime / 60) % 60, uptime % 60 ),
    'human-now': TS.ts_to_name(),
    'computer-uptime': uptime,
    'computer-now': time.time(),
    'last-recorded': float(DB.get('last_recorded', use_cache=False) or 0),
    'hits': DB.run('select sum(value) from kv where key like "%hit%"').fetchone()[0],
    'version': __version__,
    'uuid': config['uuid'],
    'next-prune': int(last_prune - (TS.unixtime('prune') - prune_duration)), 
    'load': load,
    'files': [m.path for m in psutil.Process().open_files()],
    'connections': len(psutil.Process().connections()),
    'memory': [
      # Current memory footprint in MB
      psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024), 
      
      # Maximum lifetime memory footpring in MB
      resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    ],
    'threads': [ thread.name for thread in threading.enumerate() ],
    'disk': cloud.size('.') / (1024.0 ** 3)
  }


def mail_config(parser):
  cfg = os.environ.get('CLOUD_CFG')

  parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
  args = parser.parse_args()

  if args.config is None:
    sys.stderr.write("Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option\n")
    return None

  cloud_config = configparser.ConfigParser()
  cloud_config.read(args.config)

  return config_section_map('Mailgun', cloud_config)


# Taken from https://bradgignac.com/2014/05/12/sending-email-with-python-and-the-mailgun-api.html
def send_email(config, who, subject, body, sender='Indycast Reminders <reminders@indycast.net>'):
  key = config['base_key']
  request_url = "%s/%s" % (config['base_url'].strip('/'), 'messages')

  request = requests.post(request_url, auth=('api', key), data={
    'from': sender,
    'to': who,
    'subject': subject,
    'text': re.sub('<[^<]+?>', '', body),
    'html': body
  })

  return request


def am_i_official():
  # Takes the callsign and port and queries the server for its per-instance uuid
  # If those values match our uuid then we claim that we are the official instance
  # and can do various privileged things.  Otherwise, we try not to intrude.
  global config, last_official_query

  # Don't cache a true value ... see https://github.com/kristopolous/DRR/issues/84 for details
  # Actually we'll cache it for a few seconds.
  if 'official' not in config or (not last_official_query or last_official_query + 10 < time.time()):
    endpoint = "http://%s.indycast.net:%d/uuid" % (config['callsign'], config['port'])

    try: 
      stream = urlopen(endpoint)
      data = stream.read().decode('utf-8')
      config['official'] = (data.strip() == config['uuid'])
      last_official_query = time.time()

    except Exception as ex:
      # We can't contact the server so we just return false
      # and set nothing
      return False

  return config['official']

def webserver_shutdown():
  endpoint = "http://127.0.0.1:%d/halt" % (config['port'],)

  try: 
    stream = urlopen(endpoint)
    data = stream.read()

  except:
    logging.info("Webserver already shutdown")


def public_config():
  # Returns a configuration, removing sensitive information 
  global config 
  return {k: v for k, v in list(config.items()) if k != '_private'}

def shutdown_handler(signal=signal.SIGINT, frame=None):
  # shutdown_handler is hit on the keyboard interrupt 
  shutdown()

def shutdown_real(do_restart=False):
  # During a restart shutdown we just kill the webserver.
  # The other processes will die off later.

  logging.info('total: %d' % (threading.activeCount(), ))
  # we release our main lock which signifies that the 
  # threads should die off.
  try:
    lockMap['main'].release() 
  except:
    pass

  logging.info("Releasing main lock")

  """
  for x in range(50):
    logging.info('total: %d' % (threading.activeCount(), ))
    time.sleep(0.25)
  """

  if not do_restart:
    webserver_shutdown()
    logging.info("Shutting down")
    logging.info("Uptime: %ds", TS.uptime())

    #if os.path.isfile(PIDFILE_MANAGER):
    #  os.unlink(PIDFILE_MANAGER)

    sys.exit(0)


def shutdown(do_restart=False):
  # All shutdown should be instantiated from the manager thread 
  # Make sure that all shutdown happens from the manager
  # thread
  #
  # All we do it put it in our queue ... and then trust the that
  # queue will call the real shutdown   
  if do_restart:
    queue.put(('restart', True))

  else:
    queue.put(('shutdown', True))

  return None

def manager_is_running(pid=None):
  if pid is not None:
    lockMap['main'].acquire(False)

  if lockMap['main'].acquire(False):
    try:
      lockMap['main'].release()
    except:
      pass
    return False

  return True

# From https://wiki.python.org/moin/ConfigParserExamples
def config_section_map(section, Config):
  # Takes a section in a config file and makes a dictionary
  # out of it.
  # Returns that dictionary.
  dict1 = {}

  try:
    options = Config.options(section)

  except configparser.NoSectionError as exc:
    return None

  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
        logging.info("skip: %s" % option)

    except Exception as exc:
      logging.warning("exception on %s!" % option)
      dict1[option] = None

  return dict1  
