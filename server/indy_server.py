#!/usr/bin/env python
import argparse
import ConfigParser
import json
import logging
import mad
import os
import re
import pycurl
import shutil
import sqlite3
import sys
import signal
import time
import socket
import setproctitle as SP
import lxml.etree as ET

origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
  return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)

# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper

import urllib2

from pydub import AudioSegment
from datetime import datetime
from glob import glob
from flask import Flask, request, jsonify
from multiprocessing import Process, Queue
from StringIO import StringIO

g_start_time = time.time()
g_round_ix = 0
g_queue = Queue()
g_config = {}
g_db = {}
g_streams = []
my_pid = 0

def proc_name(what):
  SP.setproctitle("ic-dlmanager")
  print "[%s] Starting" % what

def shutdown(signal, frame):
  global g_db, g_queue
  print "[%s] Shutting down" % SP.getproctitle()

  if 'conn' in g_db:
    g_db['conn'].close()

  logging.info("[%s] Shutting down through keyboard interrupt" % SP.getproctitle())
  g_queue.put('shutdown')
  sys.exit(0)

# Time related 
def to_minute(unix_time):
  if type(unix_time) is int:
    unix_time = datetime.utcfromtimestamp(unix_time)

  return unix_time.weekday() * (24 * 60) + unix_time.hour * 60 + unix_time.minute

def minute_now():
  return to_minute(datetime.utcnow())

def ago(duration):
  return time.time() - duration

# From https://wiki.python.org/moin/ConfigParserExamples
def ConfigSectionMap(section, Config):
  dict1 = {}
  options = Config.options(section)

  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
        logging.info("skip: %s" % option)

    except:
      logging.warning("exception on %s!" % option)
      dict1[option] = None

  return dict1  

# This takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
# and a 12 hour time hh:mm [ap]m and converts it to our absolute units
# with respect to the timestamp in the configuration file
def to_utc(day_str, hour):
  global g_config

  try:
    day_number = ['sun','mon','tue','wed','thu','fri','sat','sun'].index(day_str.lower())

  except e:
    return False

  time_re = re.compile('(\d{1,2}):(\d{2})([ap])m')

  time = time_re.findall(hour)

  if len(time) == 0:
    return False

  local = day_number * (60 * 60 * 24);
  local += int(time[0]) * 60
  local += int(time[1])

  if time[2] == 'p':
    local += (12 * 60)

  utc = local + g_config['offset']

  return utc


def get_time_offset():
  global g_config
  when = int(time.time())

  api_key='AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
  url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%d&key=%s" % (g_config['lat'], g_config['long'], when, api_key)
 
  stream = urllib2.urlopen(url)
  data = stream.read()
  opts = json.loads(data)

  if opts['status'] == 'OK': 
    g_config['offset'] = int(opts['rawOffset']) / 60
    return True

    # Let's do something at least
  else:
    g_config['offset'] = 0

  return False


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

    g_db['conn'].commit()

  return g_db


def register_intent(minute, duration):
  db = db_connect()

  key = str(minute) + str(duration)
  c = db['c']
  res = c.execute('select id from intents where key = ?', (key, )).fetchone()

  if res == None:
    c.execute('insert into intents(key, start, end) values(?, ?, ?)', (key, minute, minute + duration))

  else:
    c.execute('update intents set read_count = read_count + 1, accessed_at = (current_timestamp) where id = ?', (res[0], )) 

  db['conn'].commit()
  return db['c'].lastrowid
  

def should_be_recording():
  global g_config

  db = db_connect()

  current_minute = minute_now()

  intent_count = db['c'].execute(
    """select count(*) from intents where 
        start >= ? and 
        end <= ? and 
        accessed_at > datetime('now','-%s days')
    """ % g_config['expireafter'], 
    (current_minute, current_minute)
  ).fetchone()[0]

  return intent_count != 0
  

def prune():
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


def find_streams(start_query, duration):
  global g_streams
  ts_re = re.compile('(\d*).mp3')
  file_list = []
  
  end_query = start_query + duration

  for filename in glob('*.mp3'): 
    ts = ts_re.findall(filename)

    try:
      duration = mad.MadFile(filename).total_time() / (60.0 * 1000)

    except:
      logging.warning("Unable to read file %s as an mp3 file" % filename)

    start_test = to_minute(int(ts[0]))
    end_test = start_test + duration

    # If we started recording before this is fine
    # as long as we ended recording after our start
    if start_test < start_query and end_test > start_query or start_query == -1:
      file_list.append((start_test, start_test + duration, filename))
      next

    # If we started recording after the query time, this is fine
    # so long as it's before the end
    if start_test > start_query and start_test < end_query:
      file_list.append((start_test, start_test + duration, filename))
      next

  return file_list

#
# This takes a number of params:
# 
#  showname - from the incoming request url
#  feedList - this is a list of tuples in the form
#       (date, file)
#
#       corresponding to the, um, date of recording
#       and filename
#   
# It obviously returns an xml file ... I mean duh.
#
def generate_xml(showname, feed_list):
  global g_config

  base_url = 'http://%s.indycast.net/' % g_config['callsign']

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
    'copyright': g_config['callsign'],
    'description': showname,
    'language': 'en'
  }.items():
    ET.SubElement(channel, k).text = v

  for feed in feed_list:
    link = base_url + 'stream/' + feed[1]
    item = ET.SubElement(channel, 'item')
    for k,v in {
      '{%s}explicit' % nsmap['itunes']: 'no', 
      '{%s}author' % nsmap['itunes']: g_config['callsign'],
      '{%s}duration' % nsmap['itunes']: 'TODO', 
      '{%s}summary' % nsmap['itunes']: feed[0],
      '{%s}creator' % nsmap['dc']: g_config['callsign'],
      '{%s}origEnclosureLink' % nsmap['feedburner']: link,
      '{%s}origLink' % nsmap['feedburner']: base_url,
      'description': feed[0],
      'pubDate': feed[0], 
      'title': feed[0], 
      'link': feed[1],
      'copyright': g_config['callsign'],
      'guid': g_config['callsign'] + feed[0]
    }.items():
      ET.SubElement(item, k).text = v

    ET.SubElement(item, 'guid', isPermaLink="false").text = base_url

    content = ET.SubElement(item, '{%s}content' % nsmap['media'])
    content.attrib['url'] = link
    content.attrib['fileSize'] = 'TODO'
    content.attrib['type'] = 'TODO'

    content = ET.SubElement(item, 'enclosure')
    content.attrib['url'] = link
    content.attrib['length'] = 'TODO'
    content.attrib['type'] = 'TODO'

  tree = ET.ElementTree(root)

  return ET.tostring(tree, xml_declaration=True, encoding="utf-8")


def server(config):
  app = Flask(__name__)

  #
  # The path is (unix timestamp)_(duration in minutes)
  # If it exists (as in we had previously generated it)
  # then we can trivially send it.  Otherwise we need
  # to create it.
  #
  @app.route('/stream/<path:path>')
  def send_stream(path):
    # If the file doesn't exist, then we need to slice
    # it and create it based on our query.
    if not os.path.isfile(config['storage'], path):
      # find the closest timestamp
      # slice if needed
      # add up the timestamp
      return True

    return send_from_directory(config['storage'], path)

  @app.route('/heartbeat')
  def heartbeat():
    if request.remote_addr != '127.0.0.1':
      return '', 403

    stats = {
      'disk': sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f)),
      'streams': find_streams(-1, 0),
      'config': config
    }

    return jsonify(stats), 200
  
  @app.route('/<weekday>/<start>/<duration>/<name>')
  def stream(weekday, start, duration, showname):
    ts = to_utc(weekday, start)

    # This will register the intent if needed
    register_intent(ts, duration)

    # Look for streams that we have which match this query
    # and duration
    feed_list = find_streams(start_query, duration)

    # Then, taking those two things, make a feed list from them
    return generate_xml(showname, feed_list)

  if __name__ == '__main__':
    proc_name("ic-webserver")
    app.run()


def download(callsign, url):

  proc_name("ic-download")

  def cback(data): 
    global g_round_ix, g_config, g_start_time

    g_queue.put(True)
    g_round_ix += 1
    stream.write(data)
    #logging.debug(str(float(g_round_ix) / (time.time() - g_start_time)))

  fname = callsign + "-" + str(int(time.time())) + ".mp3"

  try:
    stream = open(fname, 'w')

  except:
    logging.critical("Unable to open %s. Can't record. Must exit." % (fname))
    sys.exit(-1)

  c = pycurl.Curl()
  c.setopt(c.URL, url)
  c.setopt(pycurl.WRITEFUNCTION, cback)
  c.perform()
  c.close()

  stream.close()


def spawner():
  global g_queue, g_config

  last = {
    'prune': 0,
    'offset': 0
  }

  callsign = g_config['callsign']
  url = g_config['stream']

  cascade_time = int(g_config['cascadetime'])
  cascade_buffer = int(g_config['cascadebuffer'])
  cascade_margin = cascade_time - cascade_buffer
  last_success = 0

  mode_full = (g_config['mode'].lower() == 'full')
  b_shutdown = False
  should_record = mode_full

  # Number of seconds to be cycling
  cycle_time = 5

  process = False
  process_next = False

  server_pid = Process(target=server, args=(g_config,))
  server_pid.start()

  def process_start():
    global my_pid
    my_pid += 1
    logging.info("Starting cascaded downloader #%d. Next up in %ds" % (my_pid, cascade_margin))
    process = Process(target=download, args=(callsign, url,))
    process.start()
    return process

  while True:

    #
    # We cycle this to off for every run.
    # By the time we go throug the queue
    # so long as we aren't supposed to be
    # shutting down, this should be toggled
    # to true
    #
    flag = False

    if last['prune'] < ago(24 * 60 * 60):
      prune()
      last['prune'] = time.time()

    if last['offset'] < ago(24 * 60 * 60):
      get_time_offset()
      last['offset'] = time.time()

    while not g_queue.empty():
      data = g_queue.get(False)

      if data == 'shutdown':
        b_shutdown = True
      else:
        flag = True
    
    #
    # If we are not in full mode, then we should check
    # whether we should be recording right now according
    # to our intents.
    #
    if not mode_full:
      should_record = should_be_recording()

    if should_record:

      # Didn't respond in cycle_time seconds so we respawn
      if not flag:
        if process != False and process.is_alive():
          process.terminate()
        process = False

      if not process and not b_shutdown:
        process = process_start()
        last_success = time.time()

      # If we've hit the time when we ought to cascade
      elif time.time() - last_success > cascade_margin:
        # And we haven't created the next process yet, then we start
        # it now.
        if process_next == False:
          process_next = process_start()

        # if we are past the cascade_time and we have a process_next, then
        # we should shutdown our previous process and move the pointers around
        if time.time() - last_success > cascade_time and process_next:
          logging.info("Stopping cascaded downloader")
          process.shutdown()

          # if the process_next is running then we move
          # our last_success forward to the present
          last_success = time.time()

          # we rename our process_next AS OUR process
          process = process_next

          # And then clear out the old process_next pointer
          process_next = False 

      # If our last_success stream was more than cascade_time - cascade_buffer
      # then we start our process_next
      
      # If there is still no process then we should definitely bail.
      if not process:
        return False

    #
    # The only way for the bool to be toggled off
    # is if we are not in full-mode ... we get here
    # if we should NOT be recording.  So we make sure
    # we aren't.
    #  
    else:
      if process != False and process.is_alive():
        process.terminate()
      process = False

    time.sleep(cycle_time)


def readconfig():
  global g_config

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
  parser.add_argument("-v", "--version", help="Version info")
  args = parser.parse_args()

  Config = ConfigParser.ConfigParser()
  Config.read(args.config)
  g_config = ConfigSectionMap('Main', Config)
  
  for k,v in {
    'loglevel': 'WARN',
    'expireafter': '45',
    'cascadebuffer': 15,
    'cascadetime': 60 * 2
  }.items():
    if k not in g_config:
      g_config[k] = v

  if os.path.isdir(g_config['storage']):
    #
    # There's a bug after we chdir, where the multiprocessing is trying to
    # grab the same invocation as the initial argv[0] ... so we need to make
    # sure that if a user did ./blah this will be maintained.
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

  # register_intent(123,321)
  # print should_be_recording()
  get_time_offset()
  signal.signal(signal.SIGINT, shutdown)

if __name__ == "__main__":

  # From http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice
  if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    proc_name("ic-main")
    server(g_config)

  else: 
    readconfig()      
    proc_name("ic-dlmanager")
    spawner()
