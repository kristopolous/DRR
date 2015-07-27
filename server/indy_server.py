#!/usr/bin/python -O
import argparse
import ConfigParser
import json
import logging
import lxml.etree as ET
import math
import os
import pycurl
import re
import signal
import sys
import time
import setproctitle as SP
import sqlite3
import lib.db as DB
import lib.audio as audio
import lib.ts as TS
import lib.misc as misc
import lib.cloud as cloud
import uuid
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

import urllib2
import urllib

from datetime import datetime, timedelta, date
from glob import glob
from flask import Flask, request, jsonify, Response, url_for
import flask
from subprocess import call
import subprocess
from multiprocessing import Process, Queue

g_download_pid = 0
g_params = {}
__version__ = os.popen("git describe").read().strip()

##
## Storage and file related
##
def file_find_and_make_slices(start_list, duration_min):
  """
  Given a start week minute this looks for streams in the storage 
  directory that match it - regardless of duration ... so it may return
  partial shows results.
  """
  stream_list = []

  if type(start_list) is int:
    start_list = [start_list]

  # Sort nominally - since we have unix time in the name, this should come out
  # as sorted by time for us for free.
  stitch_list = []
  db = DB.connect()

  # So we have a start list, we are about to query our database using the start_minute
  # and end_minute field ... to get end_minue we need to make use of our duration.
  #
  # timeline ->
  #
  #          ###################           << Region we want
  # start_sea#ch    end_search #           << Search
  #          V                 V
  # |     |     |     |     |     |     |  << Minute
  #          a     b     b     c
  #
  # so we want 
  #     (a) start_minute < start_search and end_minute >= start_search  ||
  #     (b) start_minute > start_search and end_minute <= end_search  ||
  #     (c) start_minute < end_search and end_minute >= end_search
  #     
  condition_list = []
  for start in start_list:
    end_search = (start + duration_min) % TS.MINUTES_PER_WEEK
    condition_list.append('start_minute < %d and end_minute >= %d' % (start, start))
    condition_list.append('start_minute > %d and end_minute >= %d and end_minute <= %d' % (start, start, end_search))
    condition_list.append('start_minute < %d and end_minute >= %d' % (end_search, end_search))

  condition_query = "((%s))" % ') or ('.join(condition_list)

  # see https://github.com/kristopolous/DRR/issues/50
  condition_query += " and start_unix < datetime(%d, 'unixepoch', 'localtime')" % (TS.sec_now() - duration_min * 60 - misc.config['cascadetime'])

  # print condition_query
  entry_list = DB.map(db['c'].execute("select * from streams where %s order by week_number * 10080 + start_minute asc" % condition_query).fetchall(), 'streams')

  # We want to make sure that we break down the stream_list into days.  We can't JUST look at the week
  # number since we permit feed requests for shows which may have multiple days.  Since this is leaky
  # data that we don't keep via our separation of concerns, we use a little hack to figure this out.
  by_episode = []
  episode = []
  cutoff_minute = 0
  current_week = 0

  for entry in entry_list:
    # look at start minute, if it's > 12 * cascade time (by default 3 hours), then we presume this is a new episode.
    if entry['start_minute'] > cutoff_minute or entry['week_number'] != current_week:
      if len(episode):
        by_episode.append(episode)

      episode = []

    cutoff_minute = entry['start_minute'] + (12 * misc.config['cascadetime']) % TS.MINUTES_PER_WEEK
    current_week = entry['week_number']

    # We know by definition that every entry in our stream_list is a valid thing we need
    # to look at.  We just need to make sure we break them down by episode
    episode.append(entry)

  if len(episode):
    by_episode.append(episode)

  #print len(by_episode), condition_query
  # Start the creation of the mp3s
  for episode in by_episode:

    # We blur the test start to a bigger window
    test_start = (episode[0]['start_minute'] / (60 * 4))

    for week_start in start_list:
      # Blur the query start to the same window
      query_start = week_start / (60 * 4)

      # This shouldn't be necessary but let's do it anyway
      if abs(query_start - test_start) <= 1:
        # Under these conditions we can say that this episode
        # can be associated with this particular start time

        # The start_minute is based on the week
        offset_start = week_start - episode[0]['start_minute']
        fname = audio.stream_name(episode, offset_start, duration_min)

        # We get the name that it will be and then append that
        stream_list.append(audio.stream_info(fname))

        # print offset_start, duration_min, episode
        audio.stitch_and_slice(episode, offset_start, duration_min)
        break

  return stream_list


def server_generate_xml(showname, feed_list, duration_min, weekday_list, start, duration_string):
  """
  This takes a number of params:
 
  showname - from the incoming request url
  feed_list - this is a list of tuples in the form (date, file)
       corresponding to the, um, date of recording and filename
   
  It obviously returns an xml file ... I mean duh.

  In the xml file we will lie about the duration to make life easier
  """
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

  base_url = 'http://%s.indycast.net:%d/' % (misc.config['callsign'], misc.config['port'])
  callsign = misc.config['callsign']

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

    itunes_duration = "%02d:00" % (duration_min % 60)
    if duration_min > 60:
      itunes_duration = "%d:%s" % (int(math.floor(duration_min / 60 )), itunes_duration)    

    for k,v in {
      'title': "%s - %s" % (showname, feed['start_date'].strftime("%Y.%m.%d")),
      'description': "%s recorded on %s" % (showname, feed['start_date'].strftime("%Y-%m-%d %H:%M:%S")),
      '{%s}explicit' % nsmap['itunes']: 'no', 
      '{%s}author' % nsmap['itunes']: callsign,
      '{%s}duration' % nsmap['itunes']: itunes_duration,
      '{%s}summary' % nsmap['itunes']: showname,
      '{%s}creator' % nsmap['dc']: callsign.upper(),
      '{%s}origEnclosureLink' % nsmap['feedburner']: link,
      '{%s}origLink' % nsmap['feedburner']: base_url,
      'pubDate': feed['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
      'link': link,
      'copyright': callsign
    }.items():
      ET.SubElement(item, k).text = v

    ET.SubElement(item, 'guid', isPermaLink="false").text = file_name

    # fileSize and length will be guessed based on 209 bytes covering
    # frame_length seconds of audio (128k/44.1k no id3)
    content = ET.SubElement(item, '{%s}content' % nsmap['media'])
    content.attrib['url'] = link
    content.attrib['fileSize'] = str(cloud.get_size(file_name))
    content.attrib['type'] = 'audio/mpeg'

    # The length of the audio we will just take as the duration
    content = ET.SubElement(item, 'enclosure')
    content.attrib['url'] = link
    content.attrib['length'] = str(cloud.get_size(file_name))
    content.attrib['type'] = 'audio/mpeg'

  tree = ET.ElementTree(root)

  return Response(ET.tostring(tree, xml_declaration=True, encoding="UTF-8"), mimetype='text/xml')


def server_error(errstr):
  """ Returns a server error as a JSON result. """
  return jsonify({'result': False, 'error':errstr}), 500
    

def server_manager(config):
  """ Main flask process that manages the end points. """
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
    """ Supports 206 partial content requests for podcast streams. """
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
      data = f.read(length + 1)

    rv = Response(
      data, 
      206,
      mimetype='audio/mpeg',
      direct_passthrough=True
    )
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length, size))

    return rv


  @app.route('/uuid')
  def my_uuid():
    """ Returns this servers uuid """
    return misc.config['uuid']

  # From http://stackoverflow.com/questions/13317536/get-a-list-of-all-routes-defined-in-the-app
  @app.route("/site-map")
  def site_map():
    """ Shows all the end points supported by the current server. """
    output = []
    for rule in app.url_map.iter_rules():

      options = {}
      for arg in rule.arguments:
        options[arg] = "[{0}]".format(arg)

      url = url_for(rule.endpoint, **options)
      line = urllib.unquote("{:25s} {}".format(rule.endpoint, url))
      output.append(line)

    return Response('\n'.join(output), mimetype='text/plain')


  @app.route('/db')
  def database():
    """ Backs up the current sqlite3 db and sends it over the net. """
    filename = '%s/%s-%s.gz' % (misc.DIR_BACKUPS, misc.config['callsign'], time.strftime('%Y%m%d-%H%M', time.localtime()))
    os.popen('sqlite3 config.db .dump | gzip -9 > %s' % filename)
    time.sleep(1)
    return flask.send_file(filename)


  @app.route('/prune')
  def prune():
    """ Starts the prune process which cleans up and offloads mp3s. """
    cloud.prune()
    return "Pruning started"


  @app.route('/slices/<path:path>')
  def send_stream(path):
    """
    Downloads a stream from the server. The path is (unix timestamp)_(duration in minutes). 
    If it exists (as in we had previously generated it) then we can trivially send it. Otherwise
    we'll just call this an error to make our lives easier.
    """

    base_dir = "%s%s/" % (config['storage'], misc.DIR_SLICES)
    fname = base_dir + path

    # If the file doesn't exist, then we need to slice it and create it based on our query.
    if not os.path.isfile(fname):
      return "File not found. Perhaps the stream is old?", 404

    return send_file_partial("%s/%s" % (base_dir, path))


  @app.route('/restart')
  def restart():
    """ Restarts an instance. """
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    shutdown_server()
    misc.queue.put(('restart', True))
    return "restarting..."

    os.chdir(cwd)


  @app.route('/upgrade')
  def upgrade():
    """
    Goes to the source directory, pulls down the latest from git
    and if the versions are different, the application restarts.
    """
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    os.system('git pull') 

    # See what the version is after the pull
    newversion = os.popen("git describe").read().strip()

    if newversion != __version__:
      os.system('pip install --user -r requirements.txt') 

      # from http://blog.petrzemek.net/2014/03/23/restarting-a-python-script-within-itself/
      shutdown_server()
      misc.queue.put(('restart', True))
      return "Upgrading from %s to %s" % (__version__, newversion)

    os.chdir(cwd)
    return 'Version %s is current' % __version__


  @app.route('/heartbeat')
  def heartbeat():
    """
    A low resource version of the /stats call ... this is invoked
    by the server health check.
    """
    return jsonify({
      'uptime': int(time.time() - misc.start_time),
    }), 200


  @app.route('/stats')
  def stats():
    """ Reports various statistical metrics on a particular server """
    misc.am_i_official()
    db = DB.connect()

    stats = {
      'intents': DB.all('intents'),
      'hits': db['c'].execute('select sum(read_count) from intents').fetchone()[0],
      'kv': DB.all('kv'),
      'uptime': int(time.time() - misc.start_time),
      'free': os.popen("df -h / | tail -1").read().strip(),
      'load': os.popen("uptime").read().strip(),
      'plist': os.popen("ps auxf | grep %s" % misc.config['callsign']).read().strip().split('\n'),
      'disk': sum(os.path.getsize(f) for f in os.listdir('.') if os.path.isfile(f)),
      'streams': DB.all('streams', sort_by='start_unix'),
      'version': __version__,
      'config': misc.public_config()
    }

    return jsonify(stats), 200
  

  @app.route('/<weekday>/<start>/<duration_string>/<showname>')
  def stream(weekday, start, duration_string, showname):
    """
    Returns an xml file based on the weekday, start and duration
    from the front end.
    """
    
    # Supports multiple weekdays
    weekday_list = weekday.split(',')

    # Duration is expressed either in minutes or in \d+hr\d+ minute
    re_minute = re.compile('^(\d+)(?:min|)$')
    re_hr_solo = re.compile('^(\d+)hr$', re.I)
    re_hr_min = re.compile('^(\d+)hr(\d+).*$', re.I)

    duration_min = False

    res = re_minute.match(duration_string)
    if res:
      duration_min = int(res.groups()[0])

      # This means that the input is just numeric.
      # This is fine for now, but we use this to construct prose such as
      # "So and so is a xxx show recorded" ... in this case, a unit is
      # nice to have there for legibility purposes.  Since we are doing
      # with our parsing of the string, we can just ammend the unit
      # to the end
      if re.match('^(\d+)$', duration_string):
        duration_string += 'min'

    else:
      res = re_hr_solo.match(duration_string)

      if res:
        duration_min = int(res.groups()[0]) * 60

      else:
        res = re_hr_min.match(duration_string)

        if res:
          duration_min = int(res.groups()[0]) * 60 + int(res.groups()[1])

    # This means we failed to parse
    if not duration_min:
      return server_error('duration "%s" is not set correctly' % duration_string)

    #
    # See https://github.com/kristopolous/DRR/issues/22:
    #
    # We're going to add 2 minutes to the duration to make sure that we get
    # the entire episode.
    #
    duration_min += 2

    start_time_list = [TS.to_utc(day, start) for day in weekday_list]
    
    if type(start_time_list[0]) is not int:
      return server_error('weekday and start times are not set correctly')

    # If we are here then it looks like our input is probably good.
    
    # Strip the .xml from the showname ... this will be used in our xml.
    showname = re.sub('.xml$', '', showname)

    # We come in with spaces as underscores so here we translate that back
    showname = re.sub('_', ' ', showname)

    # This will register the intent if needed for future recordings
    # (that is if we are in ondemand mode)
    DB.register_intent(start_time_list, duration_min)

    # Make sure that we have all of our streams registered before trying
    # to infer what we can send to the user.
    cloud.register_streams()

    # Look for streams that we have which match this query and duration.
    # This will also create slices if necessary in a sub process.
    # The list of files that returns will include this not-yet-created
    # file-name as essentially a "promise" to when it will be made.
    feed_list = file_find_and_make_slices(start_time_list, duration_min)

    # Then, taking those two things, make a feed list from them.
    return server_generate_xml(
      showname=showname, 
      feed_list=feed_list, 
      duration_min=duration_min, 
      weekday_list=weekday_list, 
      start=start, 
      duration_string=duration_string
    )

  if __name__ == '__main__':
    pid = misc.change_proc_name("%s-webserver" % config['callsign'])
    with open(misc.PIDFILE_WEBSERVER, 'w+') as f:
      f.write(str(pid))

    """
    When we do an upgrade or a restart, there's a race condition of getting to start this server
    before the previous one has cleaned up all the socket work.  So if the time is under our
    patience threshold then we sleep a second and just try again, hoping that it will work.
    """
    patience = misc.PROCESS_DELAY * 2
    attempt = 1

    start = time.time()
    while time.time() - start < patience:
      try:
        print "Listening on %s" % config['port']
        app.run(threaded=True, port=config['port'], host='0.0.0.0')
        break

      except Exception as exc:
        if time.time() - start < patience:
          print "[attempt: %d] Error, can't start server ... perhaps %s is already in use?" % (attempt, config['port'])
          attempt += 1
          time.sleep(misc.PROCESS_DELAY / 4)

##
## Stream management functions
##
def stream_should_be_recording():
  """ Queries the database and see if we ought to be recording at this moment. """

  db = DB.connect()

  current_minute = TS.minute_now()

  intent_count = db['c'].execute("""
    select count(*) from intents where 
      start >= ? and 
      end <= ? and 
      accessed_at > datetime('now','-%s days')
    """ % misc.config['expireafter'], 
    (current_minute, current_minute)
  ).fetchone()[0]

  return intent_count != 0


def stream_download(callsign, url, my_pid, fname):
  """ 
  Curl interfacing which downloads the stream to disk. 
  Follows redirects and parses out basic m3u.
  """
  global g_params

  misc.change_proc_name("%s-download" % callsign)

  nl = {'stream': False}

  def dl_stop(signal, frame):
    sys.exit(0)

  def cback(data): 
    global g_params

    if g_params['isFirst'] == True:
      g_params['isFirst'] = False
      if len(data) < 800:
        if re.match('https?://', data):
          # If we are getting a redirect then we don't mind, we
          # just put it in the stream and then we leave
          misc.queue.put(('stream', data.strip()))
          return True

        # A pls style playlist
        elif re.findall('File\d', data, re.M):
          logging.info("Found a pls, using the File1 parameter");
          matches = re.findall('File1=(.*)\n', data, re.M)
          misc.queue.put(('stream', matches[0].strip()))
          return True

    # This provides a reliable way to determine bitrate.  We look at how much 
    # data we've received between two time periods
    misc.queue.put(('heartbeat', (time.time(), len(data))))

    if not nl['stream']:
      try:
        nl['stream'] = open(fname, 'w')

      except Exception as exc:
        logging.critical("Unable to open %s. Can't record. Must exit." % fname)
        sys.exit(-1)

    nl['stream'].write(data)

    if not misc.manager_is_running():
      misc.shutdown()

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


def stream_manager():
  """
  Manager process which makes sure that the
  streams are running appropriately.
  """
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
  has_bitrate = DB.get('bitrate', use_cache=True) 
  first_time = 0
  total_bytes = 0

  cascade_time = misc.config['cascadetime']
  cascade_buffer = misc.config['cascadebuffer']
  cascade_margin = cascade_time - cascade_buffer

  last_prune = 0
  last_success = 0

  mode_full = (misc.config['mode'].lower() == 'full')
  b_shutdown = False
  should_record = mode_full

  # Number of seconds to be cycling
  cycle_time = misc.config['cycletime']

  process = False
  process_next = False

  server_pid = Process(target=server_manager, args=(misc.config,))
  server_pid.start()

  fname = False

  # A wrapper function to start a donwnload process
  def download_start(fname):
    """ Starts a process that manages the downloading of a stream. """
    global g_download_pid

    g_download_pid += 1
    logging.info("Starting cascaded downloader #%d. Next up in %ds" % (g_download_pid, cascade_margin))

    #
    # There may be a multi-second lapse time from the naming of the file to
    # the actual start of the download so we should err on that side by putting it
    # in the future by some margin
    #
    fname = '%s/%s-%d.mp3' % (misc.DIR_STREAMS, callsign, TS.sec_now(offset_sec=misc.PROCESS_DELAY))
    process = Process(target=stream_download, args=(callsign, misc.config['stream'], g_download_pid, fname))
    process.start()
    return [fname, process]

  while True:
    #
    # We cycle this to off for every run. By the time we go throug the queue so long 
    # as we aren't supposed to be shutting down, this should be toggled to true.
    #
    flag = False

    if last_prune < (time.time() - TS.ONE_DAY * misc.config['pruneevery']):
      # We just assume it can do its business in under a day
      misc.pid['prune'] = cloud.prune()
      last_prune = time.time()

    TS.get_offset()

    while not misc.queue.empty():
      what, value = misc.queue.get(False)

      # The curl proces discovered a new stream to be
      # used instead.
      if what == 'stream':
        misc.config['stream'] = value
        logging.info("Using %s as the stream now" % value)
        # We now don't toggle to flag in order to shutdown the
        # old process and start a new one

      elif what == 'shutdown':
        print "-- shutdown requested"
        b_shutdown = True

      elif what == 'restart':
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        subprocess.Popen(sys.argv)

      elif what == 'heartbeat':
        flag = True

        if not has_bitrate: 
          # If we haven't determined this stream's bitrate (which we use to estimate 
          # the amount of content is in a given archived stream), then we compute it 
          # here instead of asking the parameters of a given block and then presuming.
          total_bytes += value[1]

          # Keep track of the first time this stream started (this is where our total
          # byte count is derived from)
          if not first_time: 
            first_time = value[0]

          # Otherwise we give a large (in computer time) margin of time to confidently
          # guess the bitrate.  I didn't do great at stats in college, but in my experiments,
          # the estimation falls within 98% of the destination.  I'm pretty sure it's really
          # unlikely this will come out erroneous, but I really can't do the math, it's probably
          # a T value, but I don't know. Anyway, whatevs.
          elif (value[0] - first_time > 60):
            # We take the total bytes, calculate it over our time, in this case, 25 seconds.
            est = total_bytes / (value[0] - first_time)

            # We find the nearest 8Kb increment this matches and then scale out.
            # Then we multiply out by 8 (for _K_ B) and 8 again for K _b_.
            bitrate = int( round (est / 8000) * 8 * 8 )
            DB.get('bitrate', bitrate)

      else:
        flag = True
    
    # Check for our management process
    if not misc.manager_is_running():
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
    DB.incr('uptime', cycle_time)

    time.sleep(cycle_time)


def read_config(config):
  """
  Reads a configuration file. 
  Currently documented at https://github.com/kristopolous/DRR/wiki/Join-the-Federation
  """
  Config = ConfigParser.ConfigParser()
  Config.read(config)
  misc.config = misc.config_section_map('Main', Config)
  
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
    'port': 5000,

    # The (day) duration we should be archiving things.
    'archivedays': 21,

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
    'cloudarchive': 1.05,
    
    # Run the pruning every this many days (float)
    'pruneevery': 0.5
  }

  for k, v in defaults.items():
    if k not in misc.config:
      misc.config[k] = v
    else:
      if type(v) is int: misc.config[k] = int(misc.config[k])
      elif type(v) is float: misc.config[k] = float(misc.config[k])

  # in case someone is specifying ~/radio 
  misc.config['storage'] = os.path.expanduser(misc.config['storage'])
  misc.config['_private'] = {}

  if misc.config['cloud']:
    misc.config['cloud'] = os.path.expanduser(misc.config['cloud'])

    if os.path.exists(misc.config['cloud']):
      # If there's a cloud conifiguration file then we read that too
      cloud_config = ConfigParser.ConfigParser()
      cloud_config.read(misc.config['cloud'])
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

  # If there is an existing pid-manager, that means that 
  # there is probably another version running.
  if os.path.isfile(misc.PIDFILE_MANAGER):
    with open(misc.PIDFILE_MANAGER, 'r') as f:
      oldserver = f.readline()

      try:  
        os.kill(int(oldserver), 15)
        # We give it a few seconds to shut everything down
        # before trying to proceed
        time.sleep(misc.PROCESS_DELAY / 2)

      except:
        pass
   
  # From https://docs.python.org/2/howto/logging.html
  numeric_level = getattr(logging, misc.config['loglevel'].upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)

  logging.basicConfig(level=numeric_level, filename='indycast.log', datefmt='%Y-%m-%d %H:%M:%S',format='%(asctime)s %(message)s')

  # Increment the number of times this has been run so we can track the stability of remote 
  # servers and instances.
  DB.incr('runcount')

  # This is how we discover if we are the official server or not.
  # Look at the /uuid endpoint to see how this magic works.
  misc.config['uuid'] = str(uuid.uuid4())

  signal.signal(signal.SIGINT, misc.shutdown)
  signal.signal(signal.SIGHUP, misc.donothing)


if __name__ == "__main__":

  # From http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice
  if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    server_manager(misc.config)

  else: 
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
    parser.add_argument('--version', action='version', version='indycast %s :: July 2015' % __version__)
    args = parser.parse_args()
    read_config(args.config)      

    pid = misc.change_proc_name("%s-manager" % misc.config['callsign'])

    # This is the pid that should be killed to shut the system
    # down.
    misc.manager_is_running(pid)
    with open(misc.PIDFILE_MANAGER, 'w+') as f:
      f.write(str(pid))

    stream_manager()
