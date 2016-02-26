#!/usr/bin/python3
#import objgraph
#import pdb;pdb.set_trace()
import argparse, logging, os, pycurl, re
import re, signal, sys, time, json
import setproctitle as SP

# Make sure we are at the root directory of the process
os.chdir(os.path.dirname(os.path.realpath(__file__)))
import lib.db as DB
import lib.server as server
import lib.audio as audio
import lib.ts as TS
import lib.misc as misc
import lib.cloud as cloud

from logging.handlers import RotatingFileHandler
from datetime import timedelta, date
from glob import glob
from subprocess import Popen
from threading import Thread
from queue import Queue

g_download_pid = 0
g_download_kill_pid = 0

def stream_download(callsign, url, my_pid, file_name):
  # Curl interfacing which downloads the stream to disk. 
  # Follows redirects and parses out basic m3u.
  #pid = misc.change_proc_name("%s-download" % callsign)

  nl = {'stream': None, 'curl_handle': None, 'pid': my_pid, 'ix': 0}

  def catchall(which, what):
    logging.info("%d: %s %s" % (nl['pid'], which, str(what)))

  def catch_read(what):
    return catchall('read', what)

  def catch_debug(what, origin):
    if what != 3 and what != 0:
      return catchall('debug', json.dumps([what, origin.decode('utf-8')], ensure_ascii=False))

  def cback(data): 
    global g_download_kill_pid

    """
      if len(data):
        catchall('download', json.dumps([g_download_kill_pid, nl['pid'], len(data)]))
      else:
        catchall('download', json.dumps([g_download_kill_pid, 'no data']))
    """
    # print nl['pid'], g_download_kill_pid
    if nl['pid'] <= g_download_kill_pid or not data:
      logging.info("Stopping download #%d" % nl['pid'])
      return False

    # misc.params can fail based on a shutdown sequence.
    if misc is None or misc.params is None or not misc.manager_is_running():
      # if misc is not None:
      #  misc.shutdown()
      return False

    elif not misc.params['shutdown_time']:
      if not misc.download_ipc.empty():
        what, value = misc.download_ipc.get(False)
        if what == 'shutdown_time':
          misc.params['shutdown_time'] = value

    elif TS.unixtime('dl') > misc.params['shutdown_time']:
      raise TypeError("Download Stop")

    if misc.params['isFirst'] == True:
      misc.params['isFirst'] = False

      if len(data) < 800:
        try:
          data_string = data.decode('utf-8')
        
          if re.match('https?://', data_string):
            # If we are getting a redirect then we don't mind, we
            # just put it in the stream and then we leave
            misc.queue.put(('stream', data_string.strip()))
            return False

          # A pls style playlist
          elif re.findall('File\d', data_string, re.M):
            logging.info('%d: Found a pls, using the File1 parameter' % (nl['pid'], ))
            matches = re.findall('File1=(.*)\n', data_string, re.M)
            misc.queue.put(('stream', matches[0].strip()))
            return False

        # If it gets here it's binary ... I guess that's fine.
        except:
          pass

    # This provides a reliable way to determine bitrate.  We look at how much 
    # data we've received between two time periods
    misc.queue.put(('heartbeat', (TS.unixtime('hb'), nl['pid'], len(data))))

    if not nl['stream']:
      try:
        nl['stream'] = open(file_name, 'wb')

      except Exception as exc:
        logging.critical("%d: Unable to open %s. Can't record. Must exit." % (nl['pid'], file_name))
        return False

    nl['stream'].write(data)


  misc.params['isFirst'] = True
  curl_handle = pycurl.Curl()
  curl_handle.setopt(curl_handle.URL, url)
  curl_handle.setopt(pycurl.WRITEFUNCTION, cback)
  curl_handle.setopt(pycurl.FOLLOWLOCATION, True)

  curl_handle.setopt(pycurl.VERBOSE, 1)
  #curl_handle.setopt(pycurl.READFUNCTION, catch_read)
  curl_handle.setopt(pycurl.DEBUGFUNCTION, catch_debug)

  nl['curl_handle'] = curl_handle

  try:
    curl_handle.perform()

  except pycurl.error as exc:
    if exc.args[0] != 23:
      logging.warning("%d: Couldn't resolve or connect to %s." % (nl['pid'], url))

  except:
    logging.warning("%d: Unhandled exception" % (nl['pid'], ))
    pass

  curl_handle.close()

  if nl['stream'] and type(nl['stream']) != bool:
    nl['stream'].close()
    # This is where we are sure of the stats on this file, because
    # we just closed it ... so we can register it here.
    info = audio.stream_info(file_name)

    DB.register_stream(info)


def stream_manager():
  global g_download_kill_pid
  import random

  # Manager process which makes sure that the
  # streams are running appropriately.
  callsign = misc.config['callsign']

  #
  # AAC bitrate is some non-trivial thing that even ffprobe doesn't
  # do a great job at. This solution looks at number of bits that
  # transit over the wire given a duration of time, and then uses
  # that to compute the bitrate, since in practice, that's what
  # bitrate effectively means, and why it's such an important metric.
  #
  # This is to compute a format agnostic bitrate
  # (see heartbeat for more information)
  #
  has_bitrate = DB.get('bitrate')
  if has_bitrate and int(has_bitrate) == 0:
    has_bitrate = False

  first_time = 0
  total_bytes = 0
  normalize_delay = 6
  cycle_count = 0

  cascade_time = misc.config['cascade_time']
  cascade_buffer = misc.config['cascade_buffer']
  cascade_margin = cascade_time - cascade_buffer

  last_prune = 0
  last_success = 0
  last_heartbeat = None
  
  change_state = None
  SHUTDOWN = 1
  RESTART = 2
  shutdown_time = None
  misc.download_ipc = Queue()

  # Number of seconds to be cycling
  cycle_time = misc.config['cycle_time']

  process = None
  process_next = None

  # The manager will be the one that starts this.
  #server.manager(misc.config)
  webserver = Thread(target=server.manager, name='Webserver', args=(misc.config,))
  webserver.start()

  file_name = None

  # A wrapper function to start a donwnload process
  def download_start(file_name):
    """ Starts a process that manages the downloading of a stream. """
    global g_download_pid

    g_download_pid += 1

    #
    # There may be a multi-second lapse time from the naming of the file to
    # the actual start of the download so we should err on that side by putting it
    # in the future by some margin
    #
    file_name = '%s/%s-%s.mp3' % (misc.DIR_STREAMS, callsign, TS.ts_to_name(TS.now(offset_sec=misc.PROCESS_DELAY / 2)))
    logging.info('Starting download #%d (%s). Next up in %ds' % (g_download_pid, file_name, cascade_margin))

    process = Thread(target=stream_download, name='Download-%d:%s' % (g_download_pid, TS.ts_to_name()), args=(callsign, misc.config['stream'], g_download_pid, file_name))
    process.daemon = True
    process.start()
    return [file_name, process]


  # see https://github.com/kristopolous/DRR/issues/91:
  # Randomize prune to offload disk peaks
  prune_duration = misc.config['prune_every'] * (1.10 - random.random() / 5.0)
  misc.prune_duration = prune_duration

  last_heartbeat_tid = -1
  while True:
    #
    # We cycle this to off for every run. By the time we go throug the queue so long 
    # as we aren't supposed to be shutting down, this should be toggled to true.
    #
    if last_prune < (TS.unixtime('prune') - prune_duration):
      prune_duration = misc.config['prune_every'] * (1.10 - random.random() / 5.0)
      misc.prune_duration = prune_duration
      # We just assume it can do its business in under a day
      prune = cloud.prune()
      last_prune = TS.unixtime('prune')
      misc.last_prune = last_prune

    # Increment the amount of time this has been running
    if cycle_count % 30 == 0:
      # we only do these things occasionally, they 
      # are either not very important or are not
      # expected to change that often
      TS.get_offset()

    cycle_count += 1

    lr_set = False
    expired_heartbeat = last_heartbeat and time.time() - last_heartbeat > cycle_time * 2

    while not misc.queue.empty():
      what, value = misc.queue.get(False)
      misc.queue_dbg(what, value)

      # The curl proces discovered a new stream to be
      # used instead.
      if what == 'stream':
        misc.config['stream'] = value
        logging.info("Using %s as the stream now" % value)
        # We expire our heartbeat in order to force a new stream
        # to start
        expired_heartbeat = True

      elif what == 'db-debug':
        DB.debug()

      elif what == 'shutdown':
        change_state = SHUTDOWN

      elif what == 'restart':
        logging.info(DB.get('runcount', use_cache=False))
        cwd = os.getcwd()
        os.chdir(misc.PROCESS_PATH)
        Popen(sys.argv)
        os.chdir(cwd)

        change_state = RESTART

        # Try to record for another restart_overlap seconds - make sure that
        # we don't perpetually put this in the future due to some bug.
        if not shutdown_time:
          shutdown_time = TS.unixtime('dl') + misc.config['restart_overlap']
          logging.info("Restart requested ... shutting down download at %s" % TS.ts_to_name(shutdown_time, with_seconds=True))

          #misc.shutdown_real(do_restart=False)
          #misc.download_ipc.put(('shutdown_time', shutdown_time))

          while True:
            time.sleep(5)
            with open(misc.PIDFILE_MANAGER, 'r') as f:
              manager_pid = f.read()

            #print manager_pid, os.getpid(), manager_pid == os.getpid()
            #logging.info(DB.get('runcount', use_cache=False))
            #logging.info(('ps axf | grep [%c]%s | grep python | wc -l' % (misc.config['callsign'][0], misc.config['callsign'][1:]) ).read().strip())
            ps_out = int(os.popen('ps axf | grep [%c]%s | grep python | wc -l' % (misc.config['callsign'][0], misc.config['callsign'][1:]) ).read().strip())

            if ps_out > 1: 
              logging.info("Found %d potential candidates (need at least 2)" % ps_out)
              # This makes it a restricted soft shutdown
              misc.shutdown_real(do_restart=True)
              misc.download_ipc.put(('shutdown_time', shutdown_time))
              break

            else:
              Popen(sys.argv)
              logging.warn("Couldn't find a replacement process ... not going anywhere.");

      elif what == 'heartbeat':
        if not lr_set:
          lr_set = True
          last_heartbeat = time.time()
          last_heartbeat_tid = value[1]

          if last_heartbeat_tid < g_download_kill_pid:
            logging.warn("hb: Got a heartbeat for #%d but everything below #%d should be gone!" % (last_heartbeat_tid, g_download_kill_pid))

          DB.set('last_recorded', time.time())

        if not has_bitrate: 
          margin = 60

          # Keep track of the first time this stream started (this is where our total
          # byte count is derived from)
          if not first_time: 
            first_time = value[0]

          #
          # Otherwise we give a large (in computer time) margin of time to confidently
          # guess the bitrate.  I didn't do great at stats in college, but in my experiments,
          # the estimation falls within 98% of the destination.  I'm pretty sure it's really
          # unlikely this will come out erroneous, but I really can't do the math, it's probably
          # a T value, but I don't know. Anyway, whatevs.
          #
          # The normalize_delay here is for both he-aac+ streams which need to put in some frames
          # before the quantizing pushes itself up and for other stations which sometimes put a canned
          # message at the beginning of the stream, like "Live streaming supported by ..."
          #
          # Whe we discount the first half-dozen seconds as not being part of the total, we get a 
          # stabilizing convergence far quicker.
          #
          elif (value[0] - first_time > normalize_delay):
            # If we haven't determined this stream's bitrate (which we use to estimate 
            # the amount of content is in a given archived stream), then we compute it 
            # here instead of asking the parameters of a given block and then presuming.
            total_bytes += value[2]

            # We still give it a time period after the normalizing delay in order to build enough
            # samples to make a solid guess at what this number should be.
            if (value[0] - first_time > (normalize_delay + margin)):
              # We take the total bytes, calculate it over our time, in this case, 25 seconds.
              est = total_bytes / (value[0] - first_time - normalize_delay)

              # We find the nearest 8Kb increment this matches and then scale out.
              # Then we multiply out by 8 (for _K_ B) and 8 again for K _b_.
              bitrate = int( round (est / 1000) * 8 )
              #print("Estimated bitrate:%d total:%d est:%d denom:%d" % (bitrate, total_bytes, est, value[0] - first_time - normalize_delay) )
              if bitrate > 0:
                DB.set('bitrate', bitrate)
                has_bitrate = DB.get('bitrate')

    #if last_heartbeat:
    #  logging.info("%d heartbeat %d" % (last_heartbeat, last_heartbeat_tid))

    # Check for our management process
    if not misc.manager_is_running():
      logging.info("Manager isn't running");
      change_state = SHUTDOWN

    # we get here if we should NOT be recording.  So we make sure we aren't.
    if change_state == SHUTDOWN or (change_state == RESTART and TS.unixtime('dl') > shutdown_time):
      misc.shutdown_real()

    else:
      if not process and not change_state:
        logging.info("Failed to find downloader, starting new one")
        file_name, process = download_start(file_name)
        last_success = TS.unixtime('dl')

      # If we've hit the time when we ought to cascade
      # If our last_success stream was more than cascade_time - cascade_buffer
      # then we start our process_next
      elif TS.unixtime('dl') - last_success > cascade_margin or expired_heartbeat:
        #logging.info("heartbeat expired %s %s %d %d %d" % (type(process_next), type(process), last_success, cascade_time, TS.unixtime('dl')))

        # And we haven't created the next process yet, then we start it now.
        if not process_next:
          logging.info("Failed to find downloader, starting new one")
          file_name, process_next = download_start(file_name)

      
      # If there is still no process then we should definitely bail.
      if not process:
        misc.shutdown_real()

    #
    # This needs to be on the outside loop in case we are doing a cascade
    # outside of a full mode. In this case, we will need to shut things down
    #
    # If we are past the cascade_time and we have a process_next, then
    # we should shutdown our previous process and move the pointers around.
    #
    if not change_state and (expired_heartbeat or (TS.unixtime('dl') - last_success > cascade_time and process)):
      g_download_kill_pid += 1
      #process.terminate()

      # If the process_next is running then we move our last_success forward to the present
      last_success = TS.unixtime('dl')

      # we rename our process_next AS OUR process
      process = process_next

      # and then clear out the old process_next pointer
      process_next = None

    time.sleep(cycle_time)

def unit_convert_to_sec(value):
  if type(value) is not str:
    return value

  m = re.match('^([\-\d\.]+)(.?)', value)

  if m is None:
    return value

  value = float(m.groups()[0])
  unit = m.groups()[1].lower()

  if unit == 'y': return value * 60.0 * 60.0 * 24.0 * 365.25
  if unit == 'w': return value * 60.0 * 60.0 * 24.0 * 7.0
  if unit == 'd': return value * 60.0 * 60.0 * 24.0
  if unit == 'h': return value * 60.0 * 60.0
  if unit == 'm': return value * 60.0
  return value

def read_config(config):
  import configparser
  # Reads a configuration file. 
  # Currently documented at https://github.com/kristopolous/DRR/wiki/Join-the-Federation
  Config = configparser.ConfigParser()
  Config.read(config)
  misc.config = misc.config_section_map('Main', Config)
  misc.PROCESS_PATH = os.path.dirname(os.path.realpath(__file__))
  
  defaults = {
    # The log level to be put into the indycast.log file.
    'loglevel': 'DEBUG',

    #
    # The relative, or absolute directory to put things in
    # The default goes into the home directory to try to avoid a situation
    # where we can't read or write something on default startup - also we keep
    # it out of a dot directory intentionally so that we don't fill up a home
    # directory in some hidden path - that's really dumb.
    #
    'storage': "%s/radio" % os.path.expanduser('~'),

    # The time to prolong a download to make sure that 
    # a restart or upgrade is seamless, in seconds.
    'restart_overlap': 15,

    # The TCP port to run the server on
    'port': 5000,

    # The time in looking to see if our stream is running
    'cycle_time': 7,

    # The time to start a stream BEFORE the lapse of the cascade-time
    'cascade_buffer': 15,

    # The time between cascaded streams
    'cascade_time': '15m',

    # Cloud credentials (ec2, azure etc)
    'cloud': None,

    #
    # When to get things off local disk and store to the cloud
    # This means that after this many days data is sent remote and then 
    # retained for `archivedays`.  This makes the entire user-experience
    # a bit slower of course, and has an incurred throughput cost - but
    # it does save price VPS disk space which seems to come at an unusual
    # premium.
    #
    'disk_archive': '1.20d',

    # The (day) duration we should be archiving things.
    'cloud_archive': '14d',
    
    # Run the pruning every this many days (float)
    'prune_every': '0.5d'
  }

  for k, v in list(defaults.items()):
    if k not in misc.config:
      misc.config[k] = v

    misc.config[k] = unit_convert_to_sec(misc.config[k])

  # In case someone is specifying ~/radio 
  misc.config['storage'] = os.path.expanduser(misc.config['storage'])
  misc.config['_private'] = {}

  if misc.config['cloud']:
    misc.config['cloud'] = os.path.expanduser(misc.config['cloud'])

    if os.path.exists(misc.config['cloud']):
      # If there's a cloud conifiguration file then we read that too
      cloud_config = configparser.ConfigParser()
      cloud_config.read(misc.config['cloud'])

      # Things stored in the _private directory don't get reported back in a status
      # query.
      #
      # see https://github.com/kristopolous/DRR/issues/73 for what this is about.
      misc.config['_private']['azure'] = misc.config_section_map('Azure', cloud_config)

  if not os.path.isdir(misc.config['storage']):
    try:
      # If I can't do this, that's fine.
      os.mkdir(misc.config['storage'])

    except Exception as exc:
      # We make it from the current directory
      misc.config['storage'] = defaults['storage']

      if not os.path.isdir(misc.config['storage']):
        os.mkdir(misc.config['storage'])

  # Go to the callsign level in order to store multiple station feeds on a single
  # server in a single parent directory without forcing the user to decide what goes
  # where.
  misc.config['storage'] += '/%s/' % misc.config['callsign']
  misc.config['storage'] = re.sub('\/+', '/', misc.config['storage'])

  if not os.path.isdir(misc.config['storage']):
    os.mkdir(misc.config['storage'])

  # We have a few sub directories for storing things
  for subdir in [misc.DIR_STREAMS, misc.DIR_SLICES, misc.DIR_BACKUPS]:
    if not os.path.isdir(misc.config['storage'] + subdir):
      os.mkdir(misc.config['storage'] + subdir)

  # Now we try to do all this stuff again
  if os.path.isdir(misc.config['storage']):
    #
    # There's a bug after we chdir, where the multiprocessing is trying to grab the same 
    # invocation as the initial argv[0] ... so we need to make sure that if a user did 
    # ./blah this will be maintained.
    #
    if not os.path.isfile(misc.config['storage'] + __file__):
      os.symlink(os.path.abspath(__file__), misc.config['storage'] + __file__)

    os.chdir(misc.config['storage'])

  else:
    logging.warning("Can't find %s. Using current directory." % misc.config['storage'])

  misc.PIDFILE_MANAGER = '%s/%s' % (os.getcwd(), 'pid-manager')
  # If there is an existing pid-manager, that means that 
  # there is probably another version running.
  if os.path.isfile(misc.PIDFILE_MANAGER):
    with open(misc.PIDFILE_MANAGER, 'r') as f:
      oldserver = f.readline()

      try:  
        logging.info("Replacing our old image")
        os.kill(int(oldserver), signal.SIGUSR1)
        # We give it a few seconds to shut everything down
        # before trying to proceed
        time.sleep(misc.PROCESS_DELAY / 2)

      except:
        pass
   
  # From https://docs.python.org/2/howto/logging.html
  numeric_level = getattr(logging, misc.config['loglevel'].upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)

  logger = logging.getLogger()
  formatter = logging.Formatter(str(os.getpid()) + ':%(asctime)s:%(message)s', '%m%d_%H%M_%S')
  misc.handler = RotatingFileHandler('indycast.log', maxBytes=5000000, backupCount=2)
  misc.handler.setFormatter(formatter)
  misc.handler.setLevel(numeric_level)
  logger.setLevel(numeric_level)
  logger.addHandler(misc.handler)

  # Increment the number of times this has been run so we can track the stability of remote 
  # servers and instances.
  DB.upgrade()
  del(DB.upgrade)
  DB.incr('runcount')

  # This is how we discover if we are the official server or not.
  # Look at the /uuid endpoint to see how this magic works.
  misc.config['uuid'] = os.popen('uuidgen').read().strip()

  signal.signal(signal.SIGINT, misc.shutdown_handler)
  signal.signal(signal.SIGUSR1, misc.shutdown_handler)
  signal.signal(signal.SIGHUP, misc.do_nothing)


misc.IS_TEST = False
misc.start_time = TS.unixtime()

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
parser.add_argument('--version', action='version', version='indycast %s :: Aug 2015' % misc.__version__)
parser.add_argument("--daemon", action='store_true',  help="run as daemon")
args = parser.parse_args()
if args.daemon:
  Popen( [x for x in sys.argv if x != '--daemon'] )
  sys.exit(0)

read_config(args.config)      
del(read_config)

SP.setproctitle("%s-indycast" % misc.config['callsign'])
pid = os.getpid()

# This is the pid that should be killed to shut the system
# down.
misc.manager_is_running(pid)
with open(misc.PIDFILE_MANAGER, 'w+') as f:
  f.write(str(pid))

stream_manager()
