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
import re
import setproctitle as SP
import signal
import socket
import sqlite3
import struct
import sys
import time

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

from datetime import datetime, timedelta, date
from glob import glob
from flask import Flask, request, jsonify
import flask
from multiprocessing import Process, Queue

g_start_time = time.time()
g_queue = Queue()
g_config = {}
g_db = {}
g_pid = 0
__version__ = "0.1"

# Most common frame-length ... in practice, I haven't 
# seen other values in the real world
FRAME_LENGTH = (1152.0 / 44100)

# Everything is presumed to be weekly and on the minute
# scale. We use this to do wrap around when necessary
MINUTES_PER_WEEK = 10080

# From https://wiki.python.org/moin/ConfigParserExamples
def ConfigSectionMap(section, Config):
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


# Sets a more human-readable process name for the various parts of the system to be viewed in top/htop
def change_proc_name(what):
  SP.setproctitle(what)
  print "[%s:%d] Starting" % (what, os.getpid())


# shutdown is hit on the keyboard interrupt
def shutdown(signal = 15, frame = False):
  global g_db, g_queue, g_start_time, g_config

  title = SP.getproctitle()
  print "[%s:%d] Shutting down" % (title, os.getpid())

  if 'conn' in g_db:
    g_db['conn'].close()

  logging.info("[%s:%d] Shutting down through keyboard interrupt" % (title, os.getpid()))
  if title == ('%s-manager' % g_config['callsign']):
    logging.info("Uptime: %ds", time.time() - g_start_time)

  g_queue.put(('shutdown', True))
  sys.exit(0)


##
## Audio related functions
##
def audio_stream_info(fname):
  """
  determines the date the thing starts,
  the minute time it starts, and the duration
  """
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
    duration = audio_time_fast(fname) 

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
    'duration_sec': duration,
  }


#
# Open up an mp3 file, find all the blocks, the byte offset of the blocks, and if they
# are audio blocks, construct a crc32 mapping of some given beginning offset of the audio
# data ... this is intended for stitching.
#
def audio_crc(fname, blockcount = -1):
  frame_sig = []
  start_byte = []

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  f = open(fname, 'rb')
  while blockcount != 0:
    blockcount -= 1

    frame_start = f.tell()
    header = f.read(2)
    if header:

      if header == '\xff\xfb' or header == '\xff\xfa':
        b = ord(f.read(1))

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        frame_size = (144000 * bit_rate / samp_rate) + pad_bit

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        crc = binascii.crc32(f.read(32))

        frame_sig.append(crc)

        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - 36)

      # ID3 tag for some reason
      elif header == '\x49\x44':
        # Rest of the header
        throw_away = f.read(4)

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
        # we are at the end of file, but let's just continue.
        next

      else:
        # This helps me debug mp3 files that I'm not reading correctly.
        print "%s:%s:%s:%s %s %d" % (binascii.b2a_hex(header), header, f.read(5), fname, hex(f.tell()), len(start_byte) * FRAME_LENGTH / 60)
        break

    else:
      break

  f.close()
  return [frame_sig, start_byte]

def audio_time_fast(fname):
  crc32, offset = audio_crc(fname, 2)
  # in the fast method we get the first two frames, find out the offset
  # difference between them, take the length of the file, divide it by that
  # and then presume that will be the framecount
  frame_size = offset[1] - offset[0]
  frame_count_est = os.path.getsize(fname) / frame_size
  return FRAME_LENGTH * frame_count_est

#
# Given a file_list in a directory and a duration, this function will seek out
# adjacent files if necessary and serialize them accordingly, and then return the
# file name of an audio slice that is the combination of them.
#
def audio_stitch_and_slice(file_list, start_minute, duration_minute):
  if not file_list:
    return False

  # We presume that there is a file list we need to make 
  stitched_name = audio_stitch(file_list, force_stitch = True)

  if stitched_name:
    info = audio_stream_info(stitched_name)

  else:
    logging.warn("Unable to stitch file list")
    return -1

  # After we've stitched together the audio then we start our slice
  # by figuring our the start_minute of the slice, versus ours
  start_slice = max(start_minute - info['start_minute'], 0)

  # Now we need to take the duration of the stream we want, in minutes, and then
  # make sure that we don't exceed the length of the file.
  duration_slice = min(duration_minute, start_slice + info['duration_sec'] / 60.0)

  sliced_name = audio_slice(stitched_name, start_minute = start_slice, duration_minute = duration_slice)

  return sliced_name


def audio_serialize(file_list, duration_min):
  """
  Takes a list of ordinal tuples and makes one larger mp3 out of it. 
  :param file_list: The tuple format is (file_name, byte_start, byte_end) where byte_end == -1 means "the whole file".
  """

  first_file = file_list[0][0]

  # Our file will be the first one_duration.mp3
  name_out = "stitches/%s_%d.mp3" % (first_file[first_file.index('/') + 1:first_file.rindex('.')], duration_min)

  # If the file exists, then we just return it
  if os.path.isfile(name_out):
    return name_out

  out = open(name_out, 'wb+')

  for name, start, end in file_list:
    f = open(name, 'rb')

    f.seek(start)
    
    if end == -1:
      out.write(f.read())

    else:
      out.write(f.read(end - start))

    f.close()

  out.close()

  return name_out



def audio_slice(name_in, start_minute, end_minute = -1, duration_minute = -1):
  """
  Take some mp3 file name_in and then create a new one based on the start and end times 
  by finding the closest frames and just doing an extraction.
  """

  if duration_minute == -1:
    duration_minute = end_minute - start_minute

  else:
    end_minute = start_minute + duration_minute

  callsign, unix_time = re.findall('(\w*)-(\d+)_', name_in)[0]

  name_out = "slices/%s-%d_%d.mp3" % (callsign, int(unix_time) + start_minute * 60, duration_minute)
  start_sec = start_minute * 60.0
  end_sec = end_minute * 60.0

  if os.path.isfile(name_out):
    return name_out

  crc32, offset = audio_crc(name_in)

  frame_start = max(int(math.floor(start_sec / FRAME_LENGTH)), 0)
  frame_end = min(int(math.ceil(end_sec / FRAME_LENGTH)), len(offset) - 1)

  out = open(name_out, 'wb+')
  fin = open(name_in, 'rb')

  fin.seek(offset[frame_start])
  out.write(fin.read(offset[frame_end] - offset[frame_start]))

  fin.close()
  out.close()

  return name_out



def audio_stitch(file_list, force_stitch = False):
  """
  Take a list of files and then attempt to seamlessly stitch them 
  together by looking at their crc32 checksums of the data payload in the blocks.
  """

  first = {'name': file_list[0]}
  duration = 0

  crc32, offset = audio_crc(first['name'])

  first['crc32'] = crc32
  first['offset'] = offset

  args = [(first['name'], 0, first['offset'][-1])]
  duration += len(first['offset']) * FRAME_LENGTH

  for name in file_list[1:]:
    second = {'name': name}

    crc32, offset = audio_crc(name)

    second['crc32'] = crc32
    second['offset'] = offset

    isFound = True

    try:
      pos = second['crc32'].index(first['crc32'][-2])

      for i in xrange(5, 1, -1):
        if second['crc32'][pos - i + 2] != first['crc32'][-i]:
          isFound = False
          logging.warn("Indices do not match between %s and %s" % (first['name'], second['name']))
          break

    except Exception as exc:
      logging.warn("Cannot find indices between %s and %s" % (first['name'], second['name']))
      pos = 1
      isFound = force_stitch

    if isFound:
      args.append((second['name'], second['offset'][pos], second['offset'][-2]))
      duration += (len(second['offset']) - pos - 1) * FRAME_LENGTH
      first = second
      continue

    break

  # Since we end at the last block, we can safely pass in a file1_stop of 0
  if len(args) > 1:
    # And then we take the offset in the second['crc32'] where things began
    fname = audio_serialize(args, duration_min = int(duration / 60))
    return fname


##
## Time related functions
##
def time_to_minute(unix_time):
  if type(unix_time) is int:
    unix_time = datetime.fromtimestamp(unix_time)

  return unix_time.weekday() * (24 * 60) + unix_time.hour * 60 + unix_time.minute


# from http://code.activestate.com/recipes/521915-start-date-and-end-date-of-given-week/
def time_week_to_iso(year, week):
  d = date(year, 1, 1)

  if d.weekday() > 3:
    d = d + timedelta(7 - d.weekday())

  else:
    d = d - timedelta(d.weekday())

  dlt = timedelta(days = (week - 1) * 7)
  return d + dlt


def time_sec_now():
  return int((datetime.utcnow() + timedelta(minutes = time_get_offset())).strftime('%s'))

def time_minute_now():
  return time_to_minute(datetime.utcnow())


def time_to_utc(day_str, hour):
  """
  Take the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
  and a 12 hour time hh:mm [ap]m and converts it to our absolute units
  with respect to the timestamp in the configuration file
  """

  global g_config

  try:
    day_number = ['sun','mon','tue','wed','thu','fri','sat'].index(day_str.lower())

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

  utc = local + time_get_offset()

  return utc




def time_get_offset(force = False):
  """
  contacts the goog, giving a longitude and lattitude and gets the time 
  offset with regard to the UTC.  There's a sqlite cache entry for the offset.
  """

  offset = db_get('offset', expiry = 60 * 60 * 24)
  if not offset or force:

    when = int(time.time())

    api_key='AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
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


def db_incr(key, value = 1):
  """
  increments some key in the database by some value.  It is used
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
  sets (or replaces) a given key to a specific value.
  """

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

  return value


# db_get retrieves a value from the database, tentative on the expiry
def db_get(key, expiry=0):
  db = db_connect()

  if expiry > 0:
    # If we let things expire, we first sweep for it
    db['c'].execute('delete from kv where key = ? and created_at < (current_timestamp - ?)', (key, expiry))
    db['conn'].commit()

  res = db['c'].execute('select value, created_at from kv where key = ?', (key, )).fetchone()

  if res:
    return res[0]

  return False


#
# db_connect is a "singleton pattern" or some other fancy $10-world style of maintaining 
# the database connection throughout the execution of the script.
#
def db_connect():
  global g_db

  if 'conn' not in g_db:
    conn = sqlite3.connect('config.db')
    g_db = {'conn': conn, 'c': conn.cursor()}

    g_db['c'].execute("""CREATE TABLE IF NOT EXISTS intents(
      id    INTEGER PRIMARY KEY, 
      key   TEXT UNIQUE,
      start INTEGER, 
      end   INTEGER, 
      read_count  INTEGER DEFAULT 0,
      created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
      accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""");

    g_db['c'].execute("""CREATE TABLE IF NOT EXISTS kv(
      id    INTEGER PRIMARY KEY, 
      key   TEXT UNIQUE,
      value TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""");

    g_db['conn'].commit()

  return g_db


def db_register_intent(minute, duration):
  db = db_connect()

  key = str(minute) + ':' + str(duration)
  res = db['c'].execute('select id from intents where key = ?', (key, )).fetchone()

  if res == None:
    db['c'].execute('insert into intents(key, start, end) values(?, ?, ?)', (key, minute, minute + duration))

  else:
    db['c'].execute('update intents set read_count = read_count + 1, accessed_at = (current_timestamp) where id = ?', (res[0], )) 

  db['conn'].commit()
  return db['c'].lastrowid
  

  
##
## Storage and file related
##

# Get rid of files older than archivedays
def file_prune():
  global g_config

  db = db_connect()

  duration = int(g_config['archivedays']) * 60 * 60 * 24
  cutoff = time.time() - duration

  # Dumping old streams
  count = 0
  for f in os.listdir('.'): 
    entry = g_config['storage'] + f
  
    if os.path.isfile(entry) and os.path.getctime(entry) < cutoff:
      logging.debug("Prune: %s" % entry)
      os.unlink(entry)
      count += 1 

  logging.info("Found %d files older than %s days." % (count, g_config['archivedays']))


#
# Given a start week minute this looks for streams in the storage 
# directory that match it - regardless of duration ... so it may return
# partial shows results.
#
def file_find_streams(start, duration):
  stream_list = []
  
  end = (start + duration) % MINUTES_PER_WEEK

  # We want to make sure we only get the edges so we need to have state
  # between the iterations.
  next_valid_start_minute = 0
  current_week = 0

  file_list = glob('streams/*.mp3')
  # Sorting by date (see http://stackoverflow.com/questions/23430395/glob-search-files-in-date-order)
  file_list.sort(key=os.path.getmtime)
  stitch_list = []

  for filename in file_list:
    i = audio_stream_info(filename)

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

#
# This takes a number of params:
# 
#  showname - from the incoming request url
#  feedList - this is a list of tuples in the form (date, file)
#       corresponding to the, um, date of recording and filename
#   
# It obviously returns an xml file ... I mean duh.
#
# In the xml file we will lie about the duration to make life easier
#
def server_generate_xml(showname, feed_list, duration, start_minute):
  global g_config

  base_url = 'http://%s.indycast.net/' % g_config['callsign']
  callsign = g_config['callsign']

  nsmap = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'media': 'http://search.yahoo.com/mrss/', 
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'feedburner': 'http://rssnamespace.org/feedburner/ext/1.0'
  }

  root = ET.Element("rss", nsmap = nsmap)
  root.attrib['version'] = '2.0'

  channel = ET.SubElement(root, "channel")

  for k,v in {
    '{%s}summary' % nsmap['itunes']: showname,
    '{%s}subtitle' % nsmap['itunes']: showname,
    '{%s}category' % nsmap['itunes']: 'podcast',
    'title': showname,
    'link': base_url,
    'copyright': callsign,
    'description': showname,
    'language': 'en'
  }.items():
    ET.SubElement(channel, k).text = v

  # In our feed, we construct theoretical files which will be stitched and sliced 
  # together on-demand (lazy) if the user requests it.
  for feed in feed_list:
    # This is our file ... we have a week number, which is what we need.
    # By the existence of this feed, we are essentially saying that we have
    # a specific week at a specific minute ... so we construct that as the 
    # lazy-file name

    # Start with the start_date of the feed
    #start_of_week = time_week_to_iso(feed['start_date'].year, feed['week'])
    
    # now we add the minute offset to get a datetime version 
    #dt_start_of_stream = start_of_week + timedelta(minutes = start_minute)

    # and then make a unix time stamp from it. This will be the numeric on the file that
    # are committing to making
    #str_start_of_stream = dt_start_of_stream.strftime('%s')

    #file_name = "%s-%s_%d.mp3" % (callsign, str_start_of_stream, duration)
    file_name = feed['name']
    link = "%s%s" % (base_url, file_name)

    item = ET.SubElement(channel, 'item')

    for k,v in {
      '{%s}explicit' % nsmap['itunes']: 'no', 
      '{%s}author' % nsmap['itunes']: callsign,
      '{%s}duration' % nsmap['itunes']: str(duration * 60),
      '{%s}summary' % nsmap['itunes']: showname,
      '{%s}creator' % nsmap['dc']: callsign,
      '{%s}origEnclosureLink' % nsmap['feedburner']: link,
      '{%s}origLink' % nsmap['feedburner']: base_url,
      'description': showname,
      'pubDate': feed['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
      'title': showname,
      'link': link,
      'copyright': callsign,
      'guid': callsign + file_name
    }.items():
      ET.SubElement(item, k).text = v

    ET.SubElement(item, 'guid', isPermaLink = "false").text = base_url

    # fileSize and length will be guessed based on 209 bytes covering
    # frame_length seconds of audio (128k/44.1k no id3)
    content = ET.SubElement(item, '{%s}content' % nsmap['media'])
    content.attrib['url'] = link
    content.attrib['fileSize'] = str(os.path.getsize(file_name))
    content.attrib['type'] = 'audio/mpeg3'

    # The length of the audio we will just take as the duration
    content = ET.SubElement(item, 'enclosure')
    content.attrib['url'] = link
    content.attrib['length'] = str(duration * 60)
    content.attrib['type'] = 'audio/mpeg3'

  tree = ET.ElementTree(root)

  return ET.tostring(tree, xml_declaration=True, encoding="utf-8")


def server_error(errstr):
  return jsonify({'result': False, 'error':errstr}), 500
    
def server_manager(config):
  app = Flask(__name__)

  #
  # The path is (unix timestamp)_(duration in minutes). If it exists (as in we had 
  # previously generated it) then we can trivially send it.  Otherwise we need
  # to create it.
  #
  @app.route('/slices/<path:path>')
  def send_stream(path):
    base_dir = config['storage'] + 'slices/'
    fname = base_dir + path

    # If the file doesn't exist, then we need to slice it and create it based on our query.
    if not os.path.isfile(fname):
      # 1. Find the closest timestamp
      # Even though the file doesn't exist, we'll still get
      # a partial return on getting it's "info"
      info = audio_stream_info(fname)

      # Now we see what our start stream should be
      start_stream = file_find_streams(info['start_minute'], info['duration_sec'] / 60)

      # slice if needed
      # add up the timestamp
      return True

    return flask.send_from_directory(base_dir, path)

  @app.route('/heartbeat')
  def heartbeat():
    global g_start_time

    db = db_connect()

    stats = {
      'intents': [record for record in db['c'].execute('select * from intents').fetchall()],
      'kv': [record for record in db['c'].execute('select * from kv').fetchall()],
      'uptime': int(time.time() - g_start_time),
      'disk': sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f)),
      'streams': file_find_streams(-1, 0),
      'config': config
    }

    return jsonify(stats), 200
  
  @app.route('/<weekday>/<start>/<duration>/<showname>')
  def stream(weekday, start, duration, showname):
    
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

    start_time = time_to_utc(weekday, start)
    
    if not start_time:
      return server_error('weekday and start times are not set correctly')

    # If we are here then it looks like our input is probably good.
    
    # Strip the .xml from the showname ... this will be used in our xml.
    showname = re.sub('.xml$', '', showname)

    # This will register the intent if needed for future recordings
    # (that is if we are in ondemand mode)
    db_register_intent(start_time, duration)

    # Look for streams that we have which match this query and duration.
    feed_list = file_find_streams(start_time, duration)

    # Then, taking those two things, make a feed list from them.
    return server_generate_xml(showname, feed_list, duration, start_time)

  if __name__ == '__main__':
    change_proc_name("%s-webserver" % config['callsign'])

    start = time.time()
    try:
      app.run(port = int(config['port']), host = '0.0.0.0')

    except Exception as exc:
      if time.time() - start < 5:
        print "Error, can't start server ... perhaps %s is already in use?" % config['port']

      shutdown()

##
## Stream management functions
##

# Query the database and see if we ought to be recording at this moment
def stream_should_be_recording():
  global g_config

  db = db_connect()

  current_minute = time_minute_now()

  intent_count = db['c'].execute(
    """select count(*) from intents where 
        start >= ? and 
        end <= ? and 
        accessed_at > datetime('now','-%s days')
    """ % g_config['expireafter'], 
    (current_minute, current_minute)
  ).fetchone()[0]

  return intent_count != 0


# The curl interfacing that downloads the stream to disk
def stream_download(callsign, url, my_pid, fname):
  change_proc_name("%s-download" % callsign)

  nl = {'stream': False}

  def dl_stop(signal, frame):
    sys.exit(0)

  def cback(data): 
    global g_config, g_queue

    if len(data) < 200 and re.match('https?://', data):
      # If we are getting a redirect then we don't mind, we
      # just put it in the stream and then we leave
      g_queue.put(('stream', data.strip()))
      return True

    g_queue.put(('heartbeat', True))

    if not nl['stream']:
      try:
        nl['stream'] = open(fname, 'w')

      except Exception as exc:
        logging.critical("Unable to open %s. Can't record. Must exit." % fname)
        sys.exit(-1)

    nl['stream'].write(data)


  # signal.signal(signal.SIGTERM, dl_stop)
  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.setopt(pycurl.FOLLOWLOCATION, True)

  try:
    c.perform()

  except Exception as exc:
    logging.warning("Couldn't resolve or connect to %s." % url)

  c.close()

  if type(nl['stream']) != bool:
    nl['stream'].close()


# The manager process that makes sure that the
# streams are running appropriately
def stream_manager():
  global g_queue, g_config

  callsign = g_config['callsign']

  cascade_time = int(g_config['cascadetime'])
  cascade_buffer = int(g_config['cascadebuffer'])
  cascade_margin = cascade_time - cascade_buffer

  last_prune = 0
  last_success = 0

  mode_full = (g_config['mode'].lower() == 'full')
  b_shutdown = False
  should_record = mode_full

  # Number of seconds to be cycling
  cycle_time = int(g_config['cycletime'])

  process = False
  process_next = False

  server_pid = Process(target = server_manager, args=(g_config,))
  server_pid.start()

  fname = False

  # A wrapper function to start a donwnload process
  def download_start(fname):
    global g_pid
    g_pid += 1
    logging.info("Starting cascaded downloader #%d. Next up in %ds" % (g_pid, cascade_margin))
    fname = 'streams/%s-%d.mp3' % (callsign, time_sec_now())
    process = Process(target = stream_download, args = (callsign, g_config['stream'], g_pid, fname))
    process.start()
    return [fname, process]

  while True:

    #
    # We cycle this to off for every run. By the time we go throug the queue so long 
    # as we aren't supposed to be shutting down, this should be toggled to true.
    #
    flag = False

    yesterday = time.time() - 24 * 60 * 60
    if last_prune < yesterday:
      file_prune()
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
        b_shutdown = True

      else:
        flag = True
    
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


def read_config():
  global g_config

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
  parser.add_argument('--version', action='version', version='indycast %s :: July 2015' % __version__)
  args = parser.parse_args()

  Config = ConfigParser.ConfigParser()
  Config.read(args.config)
  g_config = ConfigSectionMap('Main', Config)
  
  defaults = {
    # The log level to be put into the indycast.log file.
    'loglevel': 'WARN',

    # The recording mode, either 'full' meaning to record everything, or != 'full' 
    # meaning to record only when an intent is matched.
    'mode': 'full',

    # The relative, or absolute directory to put things in
    'storage': 'recording',

    # The (day) time to expire an intent to record
    'expireafter': '45',

    # The TCP port to run the server on
    'port': '5000',

    # The (day) duration we should be archiving things.
    'archivedays': '7',

    # The (second) time in looking to see if our stream is running
    'cycletime': '7',

    # The (second) time to start a stream BEFORE the lapse of the cascade-time
    'cascadebuffer': 15,

    # The (second) time between cascaded streams
    'cascadetime': 60 * 15
  }

  for k,v in defaults.items():
    if k not in g_config:
      g_config[k] = v

  if not os.path.isdir(g_config['storage']):
    try:
      # If I can't do this, that's fine.
      os.mkdir(g_config['storage'])

    except Exception as exc:
      # We make it from the current directory
      g_config['storage'] = defaults['storage']

      if not os.path.isdir(g_config['storage']):
        os.mkdir(g_config['storage'])

  # We go to the callsign level in order to store multiple station feeds on a single
  # server in a single parent directory without forcing the user to decide what goes
  # where.
  g_config['storage'] += '/%s/' % g_config['callsign']
  g_config['storage'] = re.sub('\/+', '/', g_config['storage'])

  if not os.path.isdir(g_config['storage']):
    os.mkdir(g_config['storage'])

  # We have a few sub directories for storing things
  for subdir in ['streams', 'stitches', 'slices']:
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
    change_proc_name("ic-main")
    server_manager(g_config)

  else: 
    read_config()      
    change_proc_name("%s-manager" % g_config['callsign'])
    stream_manager()
