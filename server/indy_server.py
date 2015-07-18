#!/usr/bin/python -O
import argparse
import binascii
import ConfigParser
import json
import logging
import lxml.etree as ET
import math
import os
import pycurl
import marshal
import gzip
import re
import setproctitle as SP
import signal
import sqlite3
import struct
import sys
import time
import socket
import StringIO
import threading

#
# This is needed to force ipv4 on ipv6 devices. It's sometimes needed
# if there isn't a clean ipv6 route to get to the big wild internet.
# In these cases, a pure ipv6 route simply will not work.  People aren't
# always in full control of every hop ... so it's much safer to force
# ipv4 then optimistically cross our fingers.
#
origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)

# Replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2
import urllib

from datetime import datetime, timedelta, date
from glob import glob
from flask import Flask, request, jsonify, Response, url_for
import flask
from subprocess import call
import subprocess
from multiprocessing import Process, Queue

g_start_time = time.time()
g_queue = Queue()
g_config = {}
g_db = {}
g_download_pid = 0
g_manager_pid = 0
g_params = {}
__version__ = os.popen("git describe").read().strip()

# Most common frame-length ... in practice, I haven't 
# seen other values in the real world
FRAME_LENGTH = (1152.0 / 44100)

# Everything is presumed to be weekly and on the minute
# scale. We use this to do wrap around when necessary
MINUTES_PER_WEEK = 10080
ONE_DAY = 60 * 60 * 24

#
# Some stations don't start you off with a valid mp3 header
# (such as kdvs), so we have to just seek into the file
# and look for one.  This is the number of bytes we try.
# In practice, 217 appears to be enough, so we make it about
# ten times that and cross our fingers
#
MAX_HEADER_ATTEMPTS = 2048

#
# Maintain a pidfile for the manager and the webserver (which
# likes to become a zombie ... braaaainnns!) so we have to take
# care of it separately and specially - like a little retard.
#
PIDFILE_MANAGER = 'pid-manager'
PIDFILE_WEBSERVER = 'pid-webserver'

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


def change_proc_name(what):
  """
  Sets a more human-readable process name for the various 
  parts of the system to be viewed in top/htop
  """
  SP.setproctitle(what)
  print "[%s:%d] Starting" % (what, os.getpid())
  return os.getpid()


def shutdown(signal=15, frame=False):
  """ Shutdown is hit on the keyboard interrupt """
  global g_db, g_queue, g_start_time, g_config

  # Try to manually shutdown the webserver
  if os.path.isfile(PIDFILE_WEBSERVER):
    with open(PIDFILE_WEBSERVER, 'r') as f:
      webserver = f.readline()

      try:  
        os.kill(int(webserver), signal)

      except:
        pass

    os.unlink(PIDFILE_WEBSERVER)

  title = SP.getproctitle()

  print "[%s:%d] Shutting down" % (title, os.getpid())

  for instance in g_db.items():
    if 'conn' in instance:
      instance['conn'].close()

  logging.info("[%s:%d] Shutting down through signal %d" % (title, os.getpid(), signal))

  if title == ('%s-manager' % g_config['callsign']):
    logging.info("Uptime: %ds", time.time() - g_start_time)

  elif title != ('%s-webserver' % g_config['callsign']) and os.path.isfile(PIDFILE_MANAGER):
    os.unlink(PIDFILE_MANAGER)

  g_queue.put(('shutdown', True))
  sys.exit(0)


##
## Audio related functions
##
def audio_get_map(fname):
  """ Retrieves a map file associated with the mp3 """
  map_name = fname if fname.endswith('.map') else fname + '.map'

  if os.path.exists(map_name):
    f = gzip.open(map_name, 'r')
    ret = marshal.loads(f.read())
    f.close()
    return ret

  return None, None
    
def audio_list_info(file_list):
  info = audio_stream_info(file_list[0]['name'])

  # Some things are the same such as the
  # week, start_minute, start_date
  info['duration_sec'] = 0
  for item in file_list:
    info['duration_sec'] += item['duration_sec']

  info['end_minute'] = (info['duration_sec'] / 60.0 + info['duration_sec']) % MINUTES_PER_WEEK

  return info

def audio_stream_info(fname, guess_time=False):
  """
  Determines the date the thing starts,
  the minute time it starts, and the duration

  If guess_time is set, then that value is used 
  as the audio time.  It can speed things up
  by avoiding an opening of the file all together.
  
  It's sometimes an ok thing to do.
  """
  if type(fname) is not str:
    return audio_list_info(fname)

  ts_re = re.compile('-(\d*)[.|_]')
  ts = ts_re.findall(fname)

  duration = 0
  start_minute = 0
  start_date = 0

  if ts:
    unix_time = int(ts[0])
    start_minute = time_to_minute(unix_time)
    start_date = datetime.fromtimestamp(unix_time)

  try:
    duration = guess_time if guess_time else audio_time(fname) 

  except Exception as exc:
    # If we can't find a duration then we try to see if it's in the file name
    ts_re_duration = re.compile('_(\d*).mp3')
    ts = ts_re_duration.findall(fname)
    if ts:
      duration = int(ts[0]) * 60

  return {
    # The week number 
    'week': start_date.isocalendar()[1], 
    'name': fname, 
    'start_minute': start_minute, 
    'start_date': start_date, 
    'end_minute': (duration / 60.0 + start_minute) % MINUTES_PER_WEEK,
    'duration_sec': duration
  }


def audio_crc(fname, blockcount=-1, only_check=False):
  """
  Opens an mp3 file, find all the blocks, the byte offset of the blocks, and if they
  are audio blocks, construct a crc32 mapping of some given beginning offset of the audio
  data ... this is intended for stitching.
  """
  # Simply make sure that there is a map associated with the
  # mp3.  Otherwise create one.
  map_name = fname if fname.endswith('.map') else fname + '.map'

  if only_check and os.path.exists(map_name):
    return True

  crc32, offset = audio_get_map(fname)
  if crc32 is not None:
    return crc32, offset

  frame_sig = []
  start_byte = []
  first_header_seen = False
  header_attempts = 0

  #
  # Looking at the first 16 bytes of the payload yield a rate that is 99.75% unique
  # as tested over various corpi ranging from 1,000,000 - 7,000,000 blocks.
  #
  # There's an additional precautions of looking for a string of 4 matches which
  # mitigates this even further
  #
  read_size = 4

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  f = open(fname, 'rb')
  while blockcount != 0:

    if first_header_seen:
      blockcount -= 1

    else:
      header_attempts += 1 
      if header_attempts > 2:
        # Go 1 back.
        f.seek(-1, 1)

    frame_start = f.tell()
    header = f.read(2)
    if header:

      if header == '\xff\xfb' or header == '\xff\xfa':

        try:
          b = ord(f.read(1))
          # If we are at the EOF
        except:
          break

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        try:
          frame_size = (144000 * bit_rate / samp_rate) + pad_bit

          # If there's a /0 error
        except:
          continue

        if not first_header_seen:
          first_header_seen = True

          # We try to record the CBR associated with this
          # stream
          if not db_get('bitrate', use_cache = True):
            db_set('bitrate', bit_rate)

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        crc = f.read(read_size)

        frame_sig.append(crc)

        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - (read_size + 4))

      # ID3 tag for some reason
      elif header == '\x49\x44':
        # Rest of the header
        throw_away = f.read(4)

        #
        # Quoting http://id3.org/d3v2.3.0
        #
        # The ID3v2 tag size is encoded with four bytes where the most significant bit 
        # (bit 7) is set to zero in every byte, making a total of 28 bits. The zeroed 
        # bits are ignored, so a 257 bytes long tag is represented as $00 00 02 01.
        #
        candidate = struct.unpack('>I', f.read(4))[0]
        size = ((candidate & 0x007f0000) >> 2 ) | ((candidate & 0x00007f00) >> 1 ) | (candidate & 0x0000007f)
        
        f.read(size)

      # ID3 TAG -- 128 bytes long
      elif header == '\x54\x41':
        # We've already read 2 so we can go 126 forward
        f.read(126)

      elif len(header) == 1:
        # We are at the end of file, but let's just continue.
        next

      elif first_header_seen or header_attempts > MAX_HEADER_ATTEMPTS:
        print "%d[%d/%d]%s:%s:%s %s %d" % (len(frame_sig), header_attempts, MAX_HEADER_ATTEMPTS, binascii.b2a_hex(header), binascii.b2a_hex(f.read(5)), fname, hex(f.tell()), len(start_byte) * (1152.0 / 44100) / 60)

        # This means that perhaps we didn't guess the start correct so we try this again
        if len(frame_sig) == 1 and header_attempts < MAX_HEADER_ATTEMPTS:
          print "False start -- trying again"

          # seek to the first start byte + 1
          f.seek(start_byte[0] + 2)

          # discard what we thought was the first start byte and
          # frame signature
          start_byte = []
          frame_sig = []
          first_header_seen = False

        else:
          break

    else:
      break

  f.close()
  # If we get here that mans that we don't have a map
  # file yet.  So we just creat it.
  map_name = fname + '.map'
  if not os.path.exists(map_name):
    with gzip.open(map_name, 'wb') as f:
      f.write(marshal.dumps([frame_sig, start_byte]))

  return frame_sig, start_byte

def audio_time(fname):
  """
  Determines the duration of an audio file by doing some estimates based on the offsets

  Returns the audio time in seconds
  """

  # In this fast method we get the first two frames, find out the offset
  # difference between them, take the length of the file, divide it by that
  # and then presume that will be the framecount
  crc32, offset = audio_crc(fname)

  return FRAME_LENGTH * len(offset)


def audio_stitch_and_slice(file_list, start_minute, duration_minute):
  """
  Given a file_list in a directory and a duration, this function will seek out
  adjacent files if necessary and serialize them accordingly, and then return the
  file name of an audio slice that is the combination of them.
  """
  if not file_list:
    return False

  # We presume that there is a file list we need to make 
  stitched_list = audio_stitch(file_list, force_stitch=True)

  if len(stitched_list) > 1:
    info = audio_stream_info(stitched_list)

  else:
    logging.warn("Unable to stitch file list")
    return False

  # After we've stitched together the audio then we start our slice
  # by figuring our the start_minute of the slice, versus ours
  start_slice = max(start_minute - info['start_minute'], 0)

  # Now we need to take the duration of the stream we want, in minutes, and then
  # make sure that we don't exceed the length of the file.
  duration_slice = min(duration_minute, start_slice + info['duration_sec'] / 60.0)

  sliced_name = audio_list_slice(
    list_in=stitched_list, 
    start_minute=start_slice, 
    duration_minute=duration_slice
  )

  return sliced_name


def audio_list_slice_process(list_in, name_out, duration_sec, start_sec):
  global g_config
  pid = change_proc_name("%s-audioslice" % g_config['callsign'])

  out = open(name_out, 'wb+')

  for ix in range(0, len(list_in)):
    item = list_in[ix]

    # get the regular map
    crc32, offset = audio_crc(item['name'])

    if ix == len(list_in) - 1:
      frame_end = min(int(math.ceil(duration_sec / FRAME_LENGTH)), len(offset) - 1)
    else:
      frame_end = len(offset) - 1

    if ix == 0:
      frame_start = max(int(math.floor(start_sec / FRAME_LENGTH)), 0)
      duration_sec -= (item['duration_sec'] - start_sec)

    else:
      frame_start = item['start_offset']
      duration_sec -= item['duration_sec'] 

    # try and get the mp3 referred to by the map file
    fin = file_get(item['name'][:-4])

    if fin:
      fin.seek(offset[frame_start])
      out.write(fin.read(offset[frame_end] - offset[frame_start]))
      fin.close()

    # If we fail to get the mp3 file then we can suppose that
    # the map file is bad so we just wince and remove it.
    else:
      os.unlink(item['name'])
      logging.warn("Unable to find %s's corresponding mp3, deleting" % item['name'])

  out.close()

  # If we failed to do anything this is a tragedy
  # and we just dump the file
  #
  # We take files under some really nominal threshold as being invalid.
  if os.path.getsize(name_out) < 1000:
    logging.warn("Unable to create %s - no valid slices" % name_out)
    os.unlink(name_out)


def audio_list_slice(list_in, start_minute, duration_minute=-1):
  """
  Takes some stitch list, list_in and then create a new one based on the start and end times 
  by finding the closest frames and just doing an extraction.
  """
  duration_sec = duration_minute * 60.0

  first_file = list_in[0]['name']
  callsign, unix_time = re.findall('(\w*)-(\d+)', first_file)[0]

  name_out = "slices/%s-%d_%d.mp3" % (callsign, int(unix_time) + start_minute * 60, duration_minute)
  start_sec = start_minute * 60.0

  if os.path.isfile(name_out) and os.path.getsize(name_out) > 0:
    return name_out

  #
  # We may need to pull things down from the cloud so it's better if we just return
  # the eventual mp3 name here and not block.  As it turns out, pulling the blobs from 
  # the cloud is rather fast on the vpss (a matter of seconds) so by the time the user
  # requests an mp3, it will probably exist.  If it doesn't, then eh, we'll figure it out.
  #
  slice_process = Process(target=audio_list_slice_process, args=(list_in, name_out, duration_sec, start_sec))
  slice_process.start()

  return name_out


def audio_stitch(file_list, force_stitch=False):
  """
  Takes a list of files and then attempt to seamlessly stitch them 
  together by looking at their crc32 checksums of the data payload in the blocks.
  """

  first = {'name': file_list[0]}
  duration = 0

  crc32, offset = audio_crc(first['name'])

  first['crc32'] = crc32
  first['offset'] = offset

  args = [{
    'name': first['name'], 
    'start_byte': 0, 
    'start_offset': 0,
    'end_byte': first['offset'][-1],
    'start_minute': 0,
    'duration_sec': (len(first['offset']) - 1) * FRAME_LENGTH
  }]

  duration += len(first['offset']) * FRAME_LENGTH

  for name in file_list[1:]:
    second = {'name': name}

    crc32, offset = audio_crc(name)

    second['crc32'] = crc32
    second['offset'] = offset

    isFound = True

    pos = -1
    try:
      while True:
        pos = second['crc32'].index(first['crc32'][-2], pos + 1)

        for i in xrange(5, 1, -1):
          if second['crc32'][pos - i + 2] != first['crc32'][-i]:
            isFound = False
            logging.warn("Indices @%d do not match between %s and %s" % (pos, first['name'], second['name']))
            continue

        # If we got here it means that everything matches
        isFound = True
        break

    except Exception as exc:
      logging.warn("Cannot find indices between %s and %s" % (first['name'], second['name']))
      pos = 1
      isFound = force_stitch

    if isFound:
      args.append({
        'name': second['name'], 
        'start_byte': second['offset'][pos], 
        'end_byte': second['offset'][-2],
        'start_offset': pos,
        'start_minute': pos * FRAME_LENGTH,
        'duration_sec': (len(second['offset']) - pos - 1) * FRAME_LENGTH
      })

      duration += (len(second['offset']) - pos - 1) * FRAME_LENGTH
      first = second
      continue

    break

  return args


##
## Time related functions
##
def time_to_minute(unix_time):
  """ Takes a given unix time and finds the week minute corresponding to it. """
  if type(unix_time) is int:
    unix_time = datetime.fromtimestamp(unix_time)

  return unix_time.weekday() * (24 * 60) + unix_time.hour * 60 + unix_time.minute

def time_sec_now(offset_sec=0):
  """ 
  Returns the unix time with respect to the timezone of the station being recorded.
  
  Accepts an optional offset_sec to forward the time into the future
  """
  return int((datetime.utcnow() + timedelta(seconds=offset_sec, minutes=time_get_offset())).strftime('%s'))

def time_minute_now():
  """ Returns the mod 10080 week minute with respect to the timezone of the station being recorded """
  return time_to_minute(datetime.utcnow() + timedelta(minutes=time_get_offset()))

def time_to_utc(day_str, hour):
  """
  Takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
  and a 12 hour time hh:mm [ap]m and converts it to our absolute units
  with respect to the timestamp in the configuration file
  """
  global g_config

  try:
    day_number = ['mon','tue','wed','thu','fri','sat','sun'].index(day_str.lower())

  except Exception as exc:
    return False

  local = day_number * (60 * 24)

  time_re_solo = re.compile('(\d{1,2})([ap])m', re.I)
  time_re_min = re.compile('(\d{1,2}):(\d{2})([ap])m', re.I)

  time = time_re_solo.match(hour)
  if time:
    local += int(time.groups()[0]) * 60

  else:
    time = time_re_min.match(hour)

    if time:
      local += int(time.groups()[0]) * 60
      local += int(time.groups()[1])

  if not time:
    return False

  if time.groups()[-1] == 'p':
    local += (12 * 60)

  #utc = local + time_get_offset()

  return local


def time_get_offset(force=False):
  """
  Contacts the goog, giving a longitude and lattitude and gets the time 
  offset with regard to the UTC.  There's a sqlite cache entry for the offset.

  Returns an int second offset
  """

  offset = db_get('offset', expiry=ONE_DAY)
  if not offset or force:

    when = int(time.time())

    api_key = 'AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
    url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%d&key=%s" % (g_config['lat'], g_config['long'], when, api_key)
   
    stream = urllib2.urlopen(url)
    data = stream.read()
    opts = json.loads(data)

    if opts['status'] == 'OK': 
      logging.info("Location: %s | offset: %s" % (opts['timeZoneId'], opts['rawOffset']))
      offset = (int(opts['rawOffset']) + int(opts['dstOffset'])) / 60
      db_set('offset', offset)

    else:
      offset = 0

  return int(offset)


##
## Database Related functions
##
def db_incr(key, value=1):
  """
  Increments some key in the database by some value.  It is used
  to maintain statistical counters.
  """

  db = db_connect()

  try:
    db['c'].execute('insert into kv(value, key) values(?, ?)', (value, key))

  except Exception as exc:
    db['c'].execute('update kv set value = value + ? where key = ?', (value, key))

  db['conn'].commit()


def db_set(key, value):
  """ 
  Sets (or replaces) a given key to a specific value.  

  Returns the value that was sent
  """
  global g_params

  db = db_connect()
  
  # From http://stackoverflow.com/questions/418898/sqlite-upsert-not-insert-or-replace
  res = db['c'].execute('''
    INSERT OR REPLACE INTO kv (key, value, created_at) 
      VALUES ( 
        COALESCE((SELECT key FROM kv WHERE key = ?), ?),
        ?,
        current_timestamp 
    )''', (key, key, value))

  db['conn'].commit()

  g_params[key] = value

  return value


def db_get(key, expiry=0, use_cache=False):
  """ Retrieves a value from the database, tentative on the expiry """
  global g_params

  if use_cache and key in g_params:
    return g_params[key]

  db = db_connect()

  if expiry > 0:
    # If we let things expire, we first sweep for it
    db['c'].execute('delete from kv where key = ? and created_at < (current_timestamp - ?)', (key, expiry))
    db['conn'].commit()

  res = db['c'].execute('select value, created_at from kv where key = ?', (key, )).fetchone()

  if res:
    g_params[key] = res[0]
    return res[0]

  return False


def db_connect():
  """
  A "singleton pattern" or some other fancy $10-world style of maintaining 
  the database connection throughout the execution of the script.

  Returns the database instance
  """
  global g_db

  #
  # We need to have one instance per thread, as this is what
  # sqlite's driver dictates ... so we do this based on thread id.
  #
  # We don't have to worry about the different memory sharing models here.
  # Really, just think about it ... it's totally irrelevant.
  #
  thread_id = threading.current_thread().ident
  if thread_id not in g_db:
    g_db[thread_id] = {}

  instance = g_db[thread_id]

  if 'conn' not in instance:
    conn = sqlite3.connect('config.db')
    instance['conn'] = conn
    instance['c'] = conn.cursor()

    instance['c'].execute("""CREATE TABLE IF NOT EXISTS intents(
      id    INTEGER PRIMARY KEY, 
      key   TEXT UNIQUE,
      start INTEGER, 
      end   INTEGER, 
      read_count  INTEGER DEFAULT 0,
      created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
      accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""");

    instance['c'].execute("""CREATE TABLE IF NOT EXISTS kv(
      id    INTEGER PRIMARY KEY, 
      key   TEXT UNIQUE,
      value TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""");

    instance['conn'].commit()

  return instance


def db_register_intent(minute_list, duration):
  """
  Tells the server to record on a specific minute for a specific duration when
  not in full mode.  Otherwise, this is just here for statistical purposes.
  """
  db = db_connect()

  for minute in minute_list:
    key = str(minute) + ':' + str(duration)
    res = db['c'].execute('select id from intents where key = ?', (key, )).fetchone()

    if res == None:
      db['c'].execute('insert into intents(key, start, end) values(?, ?, ?)', (key, minute, minute + duration))

    else:
      db['c'].execute('update intents set read_count = read_count + 1, accessed_at = (current_timestamp) where id = ?', (res[0], )) 

    db['conn'].commit()
    return db['c'].lastrowid

  return None

  
##
## Storage and file related
##
def cloud_connect():
  from azure.storage import BlobService
  global g_config
  container = 'streams'

  blob_service = BlobService(g_config['azure']['storage_account_name'], g_config['azure']['primary_access_key'])
  blob_service.create_container(container, x_ms_blob_public_access='container')
  return blob_service, container

def cloud_unlink(path):
  fname = os.path.basename(path)
  blob_service, container = cloud_connect()
  return blob_service.delete_blob(container, path)

def cloud_put(path):
  blob_service, container = cloud_connect()

  if blob_service:
    try:
      res = blob_service.put_block_blob_from_path(
        container,
        os.path.basename(path),
        path,
        max_connections=5,
      )
      return res

    except:
      logging.debug('Unable to put %s in the cloud.' % path)

  return False


def cloud_get(path):
  blob_service, container = cloud_connect()

  if blob_service:
    fname = os.path.basename(path)
    try:
      blob_service.get_blob_to_path(
        container,
        fname,
        'streams/%s' % fname,
        max_connections=8,
      )
      return True

    except:
      logging.debug('Unable to retreive %s from the cloud.' % path)

  return False

def file_get_size(fname):
  """ Gets a file size or just plain guesses it if it doesn't exist yet. """
  if os.path.exists(fname):
    return os.path.getsize(fname)

  # Otherwise we try to parse the magical file which doesn't exist yet.
  ts_re_duration = re.compile('_(\d*).mp3')
  ts = ts_re_duration.findall(fname)

  if len(ts):
    duration_min = int(ts[0])

    bitrate = int(db_get('bitrate') or 128)

    #
    # Estimating mp3 length is actually pretty easy if you don't have ID3 headers.
    # MP3s are rated at things like 128kb/s ... well there you go.
    #
    # They consider a k to be 10^3, not 2^10
    #
    return (bitrate / 8) * (duration_min * 60) * (10 ** 3)

  # If we can't find it based on the name, then we are kinda 
  # SOL and just return 0
  return 0
 
def file_prune():
  """ Gets rid of files older than archivedays - cloud stores things if relevant """

  global g_config
  pid = change_proc_name("%s-cleanup" % g_config['callsign'])

  db = db_connect()

  duration = g_config['archivedays'] * ONE_DAY
  cutoff = time.time() - duration

  cloud_cutoff = False
  if g_config['cloud']:
    cloud_cutoff = time.time() - g_config['cloudarchive'] * ONE_DAY

  # Dump old streams and slices
  count = 0
  for fname in glob('*/*.mp3'):
    #
    # Depending on many factors this could be running for hours
    # or even days.  We wnat to make sure this isn't a blarrrghhh
    # zombie process or worse yet, still running and competing with
    # other instances of itself.
    #
    if not manager_is_running():
      shutdown()

    ctime = os.path.getctime(fname)

    # We observe the rules set up in the config.
    if ctime < cutoff:
      logging.debug("Prune: %s" % fname)
      os.unlink(fname)
      count += 1 

    elif cloud_cutoff and ctime < cloud_cutoff:
      logging.debug("Prune[cloud]: putting %s" % fname)
      cloud_put(fname)
      try:
        os.unlink(fname)
      except:
        logging.debug("Prune[cloud]: Couldn't remove %s" % fname)


  # The map names are different since there may or may not be a corresponding
  # cloud thingie associated with it.
  for fname in glob('*/*.map'):
    if ctime < cutoff:

      # If there's a cloud account at all then we need to unlink the 
      # equivalent mp3 file
      if cloud_cutoff:
        cloud_unlink(fname[:-4])

      # now only after we've deleted from the cloud can we delete the local file
      os.unlink(fname)

  logging.info("Found %d files older than %s days." % (count, g_config['archivedays']))
  return 0


def file_get(path):
  """
  If the file exists locally then we return it, otherwise
  we go out to the network store and retrieve it
  """
  if os.path.exists(path):
    return open(path, 'rb')

  else:
    res = cloud_get(path)
    if res:
      return open(path, 'rb')

    return False

    
def file_find_streams(start_list, duration):
  """
  Given a start week minute this looks for streams in the storage 
  directory that match it - regardless of duration ... so it may return
  partial shows results.
  """
  global g_config

  stream_list = []

  if type(start_list) is int:
    start_list = [start_list]

  file_list = glob('streams/*.map')

  # Sort nominally - since we have unix time in the name, this should come out
  # as sorted by time for us for free.
  file_list.sort() 
  stitch_list = []

  # TODO: This start list needs to be chronologically as opposed to 
  # every monday, then every tuesday, etc ... for multi-day stream requests
  for start in start_list:
    end = (start + duration) % MINUTES_PER_WEEK

    # We want to make sure we only get the edges so we need to have state
    # between the iterations.
    next_valid_start_minute = 0
    current_week = 0

    for filename in file_list:
      i = audio_stream_info(filename, guess_time=g_config['cascadetime'])

      if i['start_minute'] < next_valid_start_minute and i['week'] == current_week:
        stitch_list.append(filename)
        continue

      # We are only looking for starting edges of the stream
      #
      # If we started recording before this is fine as long as we ended recording after our start
      if start == -1 or (i['start_minute'] < start and i['end_minute'] > start) or (i['start_minute'] > start and i['start_minute'] < end):
        if start == -1:
          fname = filename

        else:
          fname = audio_stitch_and_slice(stitch_list, start, duration)
          stitch_list = [filename]
          next_valid_start_minute = (start + duration) % MINUTES_PER_WEEK
          current_week = i['week']

        if fname:
          stream_list.append(audio_stream_info(fname))

    if start != -1:
      fname = audio_stitch_and_slice(stitch_list, start, duration)
      if fname:
        stream_list.append(audio_stream_info(fname))

  return stream_list


def server_generate_xml(showname, feed_list, duration, weekday_list, start, duration_string):
  """
  This takes a number of params:
 
  showname - from the incoming request url
  feed_list - this is a list of tuples in the form (date, file)
       corresponding to the, um, date of recording and filename
   
  It obviously returns an xml file ... I mean duh.

  In the xml file we will lie about the duration to make life easier
  """
  global g_config

  day_map = {
    'sun': 'Sunday',
    'mon': 'Monday',
    'tue': 'Tuesday',
    'wed': 'Wednesday',
    'thu': 'Thursday',
    'fri': 'Friday',
    'sat': 'Saturday'
  }
  day_list = [ day_map[weekday] for weekday in weekday_list ]
  if len(day_list) == 1:
    week_string = day_list[0]

  else:
    # an oxford comma, how cute.
    week_string = "%s and %s" % (', '.join(day_list[:-1]), day_list[-1])

  base_url = 'http://%s.indycast.net:%s/' % (g_config['callsign'], g_config['port'])
  callsign = g_config['callsign']

  nsmap = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'media': 'http://search.yahoo.com/mrss/', 
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'feedburner': 'http://rssnamespace.org/feedburner/ext/1.0'
  }

  root = ET.Element("rss", nsmap=nsmap)
  root.attrib['version'] = '2.0'

  channel = ET.SubElement(root, "channel")

  for k,v in {
    '{%s}summary' % nsmap['itunes']: showname,
    '{%s}subtitle' % nsmap['itunes']: showname,
    '{%s}category' % nsmap['itunes']: 'podcast',
    'title': showname,
    'link': base_url,
    'copyright': callsign,
    'description': "%s is a %s show recorded every %s on %s at %s. Saved and delivered when you want it, through a volunteer network at http://indycast.net." % (showname, duration_string, week_string, callsign.upper(), start),
    'language': 'en'
  }.items():
    ET.SubElement(channel, k).text = v

  itunes_image = ET.SubElement(channel, '{%s}image' % nsmap['itunes'])
  itunes_image.attrib['href'] = 'http://indycast.net/icon/%s_1400.png' % urllib.quote(showname)

  media_image = ET.SubElement(channel, '{%s}thumbnail' % nsmap['media'])
  media_image.attrib['url'] = 'http://indycast.net/icon/%s_1400.png' % urllib.quote(showname)

  image = ET.SubElement(channel, 'image')
  for k,v in {
    'url': 'http://indycast.net/icon/%s_200.png' % urllib.quote(showname),
    'title': showname,
    'link': 'http://indycast.net'
  }.items():
    ET.SubElement(image, k).text = v

  for feed in feed_list:
    file_name = feed['name']
    link = "%s%s" % (base_url, file_name)

    item = ET.SubElement(channel, 'item')

    itunes_duration = "%02d:00" % (duration % 60)
    if duration > 60:
      itunes_duration = "%d:%s" % (int(math.floor(duration / 60 )), itunes_duration)    

    for k,v in {
      '{%s}explicit' % nsmap['itunes']: 'no', 
      '{%s}author' % nsmap['itunes']: callsign,
      '{%s}duration' % nsmap['itunes']: itunes_duration,
      '{%s}summary' % nsmap['itunes']: showname,
      '{%s}creator' % nsmap['dc']: callsign.upper(),
      '{%s}origEnclosureLink' % nsmap['feedburner']: link,
      '{%s}origLink' % nsmap['feedburner']: base_url,
      'description': "%s recorded on %s" % (showname, feed['start_date'].strftime("%Y-%m-%d %H:%M:%S")),
      'pubDate': feed['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
      'title': "%s - %s" % (showname, feed['start_date'].strftime("%Y.%m.%d")),
      'link': link,
      'copyright': callsign
    }.items():
      ET.SubElement(item, k).text = v

    ET.SubElement(item, 'guid', isPermaLink="false").text = file_name

    # fileSize and length will be guessed based on 209 bytes covering
    # frame_length seconds of audio (128k/44.1k no id3)
    content = ET.SubElement(item, '{%s}content' % nsmap['media'])
    content.attrib['url'] = link
    content.attrib['fileSize'] = str(file_get_size(file_name))
    content.attrib['type'] = 'audio/mpeg3'

    # The length of the audio we will just take as the duration
    content = ET.SubElement(item, 'enclosure')
    content.attrib['url'] = link
    content.attrib['length'] = str(duration * 60)
    content.attrib['type'] = 'audio/mpeg3'

  tree = ET.ElementTree(root)

  return Response(ET.tostring(tree, xml_declaration=True, encoding="utf-8"), mimetype='text/xml')


def server_error(errstr):
  """ Returns a server error as a JSON result """
  return jsonify({'result': False, 'error':errstr}), 500
    

def server_manager(config):
  """ Main flask process that manages the end points """
  global g_queue

  app = Flask(__name__)

  # from http://flask.pocoo.org/snippets/67/
  def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
      raise RuntimeError('Not running with the Werkzeug Server')
    func()


  # from http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
  @app.after_request
  def after_request(response):
    """ Supports 206 partial content requests for podcast streams """
    response.headers.add('Accept-Ranges', 'bytes')
    return response


  def send_file_partial(path):
    """ 
    Wrapper around send_file which handles HTTP 206 Partial Content
    (byte ranges)
    """
    range_header = request.headers.get('Range', None)
    if not range_header: 
      return flask.send_file(path)
    
    size = os.path.getsize(path)    
    byte1, byte2 = 0, None
    
    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()
    
    if g[0]: 
      byte1 = int(g[0])

    if g[1]: 
      byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
      length = byte2 - byte1
    
    data = None
    with open(path, 'rb') as f:
      f.seek(byte1)
      data = f.read(length)

    rv = Response(
      data, 
      206,
      mimetype = 'audio/mpeg',
      direct_passthrough=True
    )
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

    return rv


  # From http://stackoverflow.com/questions/13317536/get-a-list-of-all-routes-defined-in-the-app
  @app.route("/site-map")
  def site_map():
    """ Shows all the end points supported by the current server """
    output = []
    for rule in app.url_map.iter_rules():

      options = {}
      for arg in rule.arguments:
        options[arg] = "[{0}]".format(arg)

      url = url_for(rule.endpoint, **options)
      line = urllib.unquote("{:25s} {}".format(rule.endpoint, url))
      output.append(line)

    return Response('\n'.join(output), mimetype='text/plain')


  @app.route('/slices/<path:path>')
  def send_stream(path):
    """
    Downloads a stream from the server. The path is (unix timestamp)_(duration in minutes). 
    If it exists (as in we had previously generated it) then we can trivially send it. Otherwise
    we'll just call this an error to make our lives easier.
    """

    base_dir = config['storage'] + 'slices/'
    fname = base_dir + path

    # If the file doesn't exist, then we need to slice it and create it based on our query.
    if not os.path.isfile(fname):
      return "File not found. Perhaps the stream is old?", 404

    return send_file_partial("%s/%s" % (base_dir, path))


  @app.route('/restart')
  def restart():
    """ Restarts an instance """
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    shutdown_server()
    g_queue.put(('restart', True))
    return "restarting..."

    os.chdir(cwd)


  @app.route('/upgrade')
  def upgrade():
    """
    Goes to the source directory, pulls down the latest from git
    and if the versions are different, the application restarts
    """
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    os.system('git pull') 
    os.system('pip install --user -r requirements.txt') 

    # See what the version is after the pull
    newversion = os.popen("git describe").read().strip()

    if newversion != __version__:
      # from http://blog.petrzemek.net/2014/03/23/restarting-a-python-script-within-itself/
      shutdown_server()
      g_queue.put(('restart', True))
      return "Upgrading from %s to %s" % (__version__, newversion)

    os.chdir(cwd)
    return 'Version %s is current' % __version__


  @app.route('/heartbeat')
  def heartbeat():
    """
    A low resource version of the /stats call ... this is invoked
    by the server health check 
    """
    global g_start_time

    return jsonify({
      'uptime': int(time.time() - g_start_time),
      'version': __version__
    }), 200


  @app.route('/stats')
  def stats():
    """ Reports various statistical metrics on a particular server """
    global g_start_time

    db = db_connect()

    stats = {
      'intents': [record for record in db['c'].execute('select * from intents').fetchall()],
      'hits': db['c'].execute('select sum(read_count) from intents').fetchone()[0],
      'kv': [record for record in db['c'].execute('select * from kv').fetchall()],
      'uptime': int(time.time() - g_start_time),
      'free': os.popen("df -h / | tail -1").read().strip(),
      'disk': sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f)),
      #'streams': file_find_streams(-1, 0),
      'version': __version__,
      'config': config
    }

    return jsonify(stats), 200
  

  @app.route('/<weekday>/<start>/<duration>/<showname>')
  def stream(weekday, start, duration, showname):
    """
    Returns an xml file based on the weekday, start and duration
    from the front end.
    """
    
    # Supports multiple weekdays
    weekday_list = weekday.split(',')

    duration_string = duration

    # Duration is expressed either in minutes or in \d+hr\d+ minute
    re_minute = re.compile('^(\d+)$')
    re_hr_solo = re.compile('^(\d+)hr$', re.I)
    re_hr_min = re.compile('^(\d+)hr(\d+).*$', re.I)

    res = re_minute.match(duration)
    if res:
      duration = int(res.groups()[0])

    else:
      res = re_hr_solo.match(duration)

      if res:
        duration = int(res.groups()[0]) * 60

      else:
        res = re_hr_min.match(duration)

        if res:
          duration = int(res.groups()[0]) * 60 + int(res.groups()[1])

    # This means we failed to parse
    if type(duration) is str:
      return server_error('duration "%s" is not set correctly' % duration)

    #
    # See https://github.com/kristopolous/DRR/issues/22:
    #
    # We're going to add 2 minutes to the duration to make sure that we get
    # the entire episode.
    #
    duration += 2

    start_time_list = [time_to_utc(day, start) for day in weekday_list]
    
    if not start_time_list[0]:
      return server_error('weekday and start times are not set correctly')

    # If we are here then it looks like our input is probably good.
    
    # Strip the .xml from the showname ... this will be used in our xml.
    showname = re.sub('.xml$', '', showname)

    # We come in with spaces as underscores so here we translate that back
    showname = re.sub('_', ' ', showname)

    # This will register the intent if needed for future recordings
    # (that is if we are in ondemand mode)
    db_register_intent(start_time_list, duration)

    # Look for streams that we have which match this query and duration.
    feed_list = file_find_streams(start_time_list, duration)

    # Then, taking those two things, make a feed list from them.
    return server_generate_xml(
      showname=showname, 
      feed_list=feed_list, 
      duration=duration, 
      weekday_list=weekday_list, 
      start=start, 
      duration_string=duration_string
    )

  if __name__ == '__main__':
    pid = change_proc_name("%s-webserver" % config['callsign'])
    with open(PIDFILE_WEBSERVER, 'w+') as f:
      f.write(str(pid))

    """
    When we do an upgrade or a restart, there's a race condition of getting to start this server
    before the previous one has cleaned up all the socket work.  So if the time is under our
    patience threshold then we sleep a second and just try again, hoping that it will work.
    """
    patience = PROCESS_DELAY * 2
    attempt = 1

    start = time.time()
    while time.time() - start < patience:
      try:
        print "Listening on %s" % config['port']
        app.run(threaded=True, port=int(config['port']), host='0.0.0.0')
        break

      except Exception as exc:
        if time.time() - start < patience:
          print "[attempt: %d] Error, can't start server ... perhaps %s is already in use?" % (attempt, config['port'])
          attempt += 1
          time.sleep(PROCESS_DELAY / 4)

##
## Stream management functions
##
def stream_should_be_recording():
  """ Queries the database and see if we ought to be recording at this moment """
  global g_config

  db = db_connect()

  current_minute = time_minute_now()

  intent_count = db['c'].execute("""
    select count(*) from intents where 
      start >= ? and 
      end <= ? and 
      accessed_at > datetime('now','-%s days')
    """ % g_config['expireafter'], 
    (current_minute, current_minute)
  ).fetchone()[0]

  return intent_count != 0


def stream_download(callsign, url, my_pid, fname):
  """ 
  Curl interfacing which downloads the stream to disk. 
  Follows redirects and parses out basic m3u
  """
  global g_params

  change_proc_name("%s-download" % callsign)

  nl = {'stream': False}

  def dl_stop(signal, frame):
    sys.exit(0)

  def cback(data): 
    global g_config, g_queue, g_params

    if g_params['isFirst'] == True:
      g_params['isFirst'] = False
      if len(data) < 800:
        if re.match('https?://', data):
          # If we are getting a redirect then we don't mind, we
          # just put it in the stream and then we leave
          g_queue.put(('stream', data.strip()))
          return True

        # A pls style playlist
        elif re.findall('File\d', data, re.M):
          logging.info("Found a pls, using the File1 parameter");
          matches = re.findall('File1=(.*)\n', data, re.M)
          g_queue.put(('stream', matches[0].strip()))
          return True

    g_queue.put(('heartbeat', True))

    if not nl['stream']:
      try:
        nl['stream'] = open(fname, 'w')

      except Exception as exc:
        logging.critical("Unable to open %s. Can't record. Must exit." % fname)
        sys.exit(-1)

    nl['stream'].write(data)

    if not manager_is_running():
      shutdown()

  # signal.signal(signal.SIGTERM, dl_stop)
  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.setopt(pycurl.FOLLOWLOCATION, True)
  g_params['isFirst'] = True

  try:
    c.perform()

  except Exception as exc:
    logging.warning("Couldn't resolve or connect to %s." % url)

  c.close()

  if type(nl['stream']) != bool:
    nl['stream'].close()


def manager_is_running():
  """
  Checks to see if the manager is still running or if we should 
  shutdown.  It works by sending a signal(0) to a pid and seeing
  if that fails
  """
  global g_manager_pid

  try:
    os.kill(g_manager_pid, 0)
    return True

  except:
    return False


def stream_manager():
  """
  Manager process which makes sure that the
  streams are running appropriately
  """
  global g_queue, g_config

  callsign = g_config['callsign']

  cascade_time = g_config['cascadetime']
  cascade_buffer = g_config['cascadebuffer']
  cascade_margin = cascade_time - cascade_buffer

  last_prune = 0
  last_success = 0

  mode_full = (g_config['mode'].lower() == 'full')
  b_shutdown = False
  should_record = mode_full

  # Number of seconds to be cycling
  cycle_time = g_config['cycletime']

  process = False
  process_next = False

  server_pid = Process(target=server_manager, args=(g_config,))
  server_pid.start()

  fname = False

  # A wrapper function to start a donwnload process
  def download_start(fname):
    """ Starts a process that manages the downloading of a stream."""

    global g_download_pid
    g_download_pid += 1
    logging.info("Starting cascaded downloader #%d. Next up in %ds" % (g_download_pid, cascade_margin))

    #
    # There may be a multi-second lapse time from the naming of the file to
    # the actual start of the download so we should err on that side by putting it
    # in the future by some margin
    #
    fname = 'streams/%s-%d.mp3' % (callsign, time_sec_now(offset_sec=PROCESS_DELAY))
    process = Process(target=stream_download, args=(callsign, g_config['stream'], g_download_pid, fname))
    process.start()
    return [fname, process]

  while True:
    #
    # We cycle this to off for every run. By the time we go throug the queue so long 
    # as we aren't supposed to be shutting down, this should be toggled to true.
    #
    flag = False

    if last_prune < (time.time() - ONE_DAY * g_config['pruneevery']):
      # We just assume it can do its business in under a day
      prune_process = Process(target=file_prune)
      prune_process.start()
      last_prune = time.time()

    time_get_offset()

    while not g_queue.empty():
      what, value = g_queue.get(False)

      # The curl proces discovered a new stream to be
      # used instead.
      if what == 'stream':
        g_config['stream'] = value
        logging.info("Using %s as the stream now" % value)
        # We now don't toggle to flag in order to shutdown the
        # old process and start a new one

      elif what == 'shutdown':
        print "-- shutdown"
        b_shutdown = True

      elif what == 'restart':
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        subprocess.Popen(sys.argv)

      else:
        flag = True
    
    # Check for our management process
    if not manager_is_running():
      logging.info("Manager isn't running");
      b_shutdown = True

    #
    # If we are not in full mode, then we should check whether we should be 
    # recording right now according to our intents.
    #
    if not mode_full:
      should_record = stream_should_be_recording()

    if should_record:
      # Didn't respond in cycle_time seconds so we respawn
      if not flag:
        if process and process.is_alive():
          process.terminate()
        process = False

      if not process and not b_shutdown:
        fname, process = download_start(fname)
        last_success = time.time()

      # If we've hit the time when we ought to cascade
      elif time.time() - last_success > cascade_margin:

        # And we haven't created the next process yet, then we start it now.
        if not process_next:
          fname, process_next = download_start(fname)

      # If our last_success stream was more than cascade_time - cascade_buffer
      # then we start our process_next
      
      # If there is still no process then we should definitely bail.
      if not process:
        return False

    #
    # The only way for the bool to be toggled off is if we are not in full-mode ... 
    # we get here if we should NOT be recording.  So we make sure we aren't.
    #  
    else:
      if process and process.is_alive():
        process.terminate()

      if process_next and process_next.is_alive():
        process_next.terminate()

      process_next = process = False

    #
    # This needs to be on the outside loop in case we are doing a cascade
    # outside of a full mode. In this case, we will need to shut things down
    #
    # If we are past the cascade_time and we have a process_next, then
    # we should shutdown our previous process and move the pointers around.
    #
    if time.time() - last_success > cascade_time and process:
      logging.info("Stopping cascaded downloader")
      process.terminate()

      # If the process_next is running then we move our last_success forward to the present
      last_success = time.time()

      # we rename our process_next AS OUR process
      process = process_next

      # And then clear out the old process_next pointer
      process_next = False 

    # Increment the amount of time this has been running
    db_incr('uptime', cycle_time)

    time.sleep(cycle_time)


def make_maps():
  pid = change_proc_name("%s-mapmaker" % g_config['callsign'])
  for fname in glob('streams/*.mp3'):

    if not manager_is_running():
      shutdown()

    audio_crc(fname, only_check=True)

  return 0

def read_config(config):
  """
  Reads a configuration file. 
  Currently documented at https://github.com/kristopolous/DRR/wiki/Join-the-Federation
  """
  global g_config

  Config = ConfigParser.ConfigParser()
  Config.read(config)
  g_config = config_section_map('Main', Config)
  
  defaults = {
    # The log level to be put into the indycast.log file.
    'loglevel': 'WARN',

    # The recording mode, either 'full' meaning to record everything, or != 'full' 
    # meaning to record only when an intent is matched.
    'mode': 'full',

    # The relative, or absolute directory to put things in
    'storage': "%s/radio" % os.path.expanduser('~'),

    # The (day) time to expire an intent to record
    'expireafter': 45,

    # The TCP port to run the server on
    'port': '5000',

    # The (day) duration we should be archiving things.
    'archivedays': 14,

    # The (second) time in looking to see if our stream is running
    'cycletime': 7,

    # The (second) time to start a stream BEFORE the lapse of the cascade-time
    'cascadebuffer': 15,

    # The (second) time between cascaded streams
    'cascadetime': 60 * 15,

    # Cloud credenials (ec2, azure etc)
    'cloud': False,

    #
    # When to get things off local disk and store to the cloud
    # This means that after this many days data is sent remote and then 
    # retained for `archivedays`.  This makes the entire user-experience
    # a bit slower of course, and has an incurred throughput cost - but
    # it does save price VPS disk space which seems to come at an unusual
    # premium.
    #
    'cloudarchive': 2,
    
    # Run the pruning every this many days (float)
    'pruneevery': 0.5
  }

  for k, v in defaults.items():
    if k not in g_config:
      g_config[k] = v
    else:
      if type(v) is int: g_config[k] = int(g_config[k])
      elif type(v) is float: g_config[k] = float(g_config[k])

  # in case someone is specifying ~/radio 
  g_config['storage'] = os.path.expanduser(g_config['storage'])

  if g_config['cloud']:
    g_config['cloud'] = os.path.expanduser(g_config['cloud'])

    if os.path.exists(g_config['cloud']):
      # If there's a cloud conifiguration file then we read that too
      cloud_config = ConfigParser.ConfigParser()
      cloud_config.read(g_config['cloud'])
      g_config['azure'] = config_section_map('Azure', cloud_config)

  if not os.path.isdir(g_config['storage']):
    try:
      # If I can't do this, that's fine.
      os.mkdir(g_config['storage'])

    except Exception as exc:
      # We make it from the current directory
      g_config['storage'] = defaults['storage']

      if not os.path.isdir(g_config['storage']):
        os.mkdir(g_config['storage'])

  # Go to the callsign level in order to store multiple station feeds on a single
  # server in a single parent directory without forcing the user to decide what goes
  # where.
  g_config['storage'] += '/%s/' % g_config['callsign']
  g_config['storage'] = re.sub('\/+', '/', g_config['storage'])

  if not os.path.isdir(g_config['storage']):
    os.mkdir(g_config['storage'])

  # We have a few sub directories for storing things
  for subdir in ['streams', 'slices']:
    if not os.path.isdir(g_config['storage'] + subdir):
      os.mkdir(g_config['storage'] + subdir)

  # Now we try to do all this stuff again
  if os.path.isdir(g_config['storage']):
    #
    # There's a bug after we chdir, where the multiprocessing is trying to grab the same 
    # invocation as the initial argv[0] ... so we need to make sure that if a user did 
    # ./blah this will be maintained.
    #
    if not os.path.isfile(g_config['storage'] + __file__):
      os.symlink(os.path.abspath(__file__), g_config['storage'] + __file__)

    os.chdir(g_config['storage'])

  else:
    logging.warning("Can't find %s. Using current directory." % g_config['storage'])

  # If there is an existing pid-manager, that means that 
  # there is probably another version running.
  if os.path.isfile(PIDFILE_MANAGER):
    with open(PIDFILE_MANAGER, 'r') as f:
      oldserver = f.readline()

      try:  
        os.kill(int(oldserver), 15)
        # We give it a few seconds to shut everything down
        # before trying to proceed
        time.sleep(PROCESS_DELAY / 2)

      except:
        pass
   
  # From https://docs.python.org/2/howto/logging.html
  numeric_level = getattr(logging, g_config['loglevel'].upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)

  logging.basicConfig(level=numeric_level, filename='indycast.log', datefmt='%Y-%m-%d %H:%M:%S',format='%(asctime)s %(message)s')

  #
  # Increment the number of times this has been run so we can track the stability of remote 
  # servers and instances.
  #
  db_incr('runcount')

  signal.signal(signal.SIGINT, shutdown)


if __name__ == "__main__":

  # From http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice
  if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    server_manager(g_config)

  else: 
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
    parser.add_argument('--version', action='version', version='indycast %s :: July 2015' % __version__)
    args = parser.parse_args()
    read_config(args.config)      

    map_pid = Process(target=make_maps, args=())
    map_pid.start()

    pid = change_proc_name("%s-manager" % g_config['callsign'])

    # This is the pid that should be killed to shut the system
    # down.
    g_manager_pid = pid
    with open(PIDFILE_MANAGER, 'w+') as f:
      f.write(str(pid))

    stream_manager()
