#!/usr/bin/python -O
import objgraph
objgraph.show_growth()
import argparse
import logging
import os
import pycurl
import re
import signal
import sys
import time
import setproctitle as SP

import lib.db as DB
import lib.server as server
import lib.audio as audio
import lib.ts as TS
import lib.misc as misc
import lib.cloud as cloud

from logging.handlers import RotatingFileHandler
from datetime import timedelta, date
from glob import glob
from flask import Flask, request, jsonify, Response, url_for, redirect, send_file
from subprocess import Popen
from multiprocessing import Process, Queue

g_download_pid = 0

##
## Storage and file related
##
def server_manager(config):
  # Main flask process that manages the end points. 
  app = Flask(__name__)

  def webserver_shutdown(signal=15, frame=None):
    title = SP.getproctitle()
    logging.info("[%s:%d] Shutting down" % (title, os.getpid()))
    request.environ.get('werkzeug.server.shutdown')()

  def success(message):
    return jsonify({'res': True, 'message': message}), 200

  def fail(message):
    return jsonify({'res': False, 'message': message}), 500

  # from http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
  @app.after_request
  def after_request(response):
    # Supports 206 partial content requests for podcast streams. 
    response.headers.add('Accept-Ranges', 'bytes')
    logging.info('ua - %s' % request.headers.get('User-Agent'))
    return response


  def send_file_partial(path, requested_path, file_name=None):
    # Wrapper around send_file which handles HTTP 206 Partial Content
    # (byte ranges)

    # If we requested something that isn't around, then we bail.
    if not os.path.exists(path):
     return "File %s not found. Perhaps the stream is old?" % requested_path, 404

    range_header = request.headers.get('Range', None)
    if not range_header: 
      with open(path, 'rb') as f:
        data = f.read()

      rv = Response( data, 200, mimetype=audio.our_mime(), direct_passthrough=True )
      disposition = 'attachment;'

      if not file_name:
        file_name = os.path.basename(path)
        
      disposition += ' filename="%s"' % file_name

      rv.headers.add('Content-Disposition', disposition)
      return rv
    
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

    rv = Response( data, 206, mimetype=audio.our_mime(), direct_passthrough=True )
    disposition = 'attachment;'

    if file_name:
      disposition += ' file_name="%s"' % file_name

    rv.headers.add('Content-Disposition', disposition)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length, size))

    return rv

  # From http://stackoverflow.com/questions/13317536/get-a-list-of-all-routes-defined-in-the-app
  @app.route("/help")
  def site_map():
    """ 
    Shows all the end points supported by the current server, the options 
    and the documentation.
    """
    output = ['-=#| Welcome to indycast %s API help |#=-' % misc.__version__, '']

    for rule in app.url_map.iter_rules():

      if rule.endpoint == 'static': continue
     
      options = {}
      for arg in rule.arguments:
        options[arg] = "[{0}]".format(arg)

      url = url_for(rule.endpoint, **options)
      line = "{:15s} {}".format(url, app.view_functions[rule.endpoint].__doc__)
      output.append(line)
      output.append("")

    return Response('\n'.join(output), mimetype='text/plain')


  @app.route('/uuid')
  def my_uuid():
    """ 
    Returns this server's uuid which is generated each time it is run.
    This is used to determine whether this is the official server or not.
    """
    return misc.config['uuid']


  @app.route('/db')
  def database():
    """ 
    Backs up the current sqlite3 db and sends a gzipped version of it as the response.
    """
    filename = '%s/%s-%s.gz' % (misc.DIR_BACKUPS, misc.config['callsign'], time.strftime('%Y%m%d-%H%M', time.localtime()))
    os.popen('sqlite3 config.db .dump | gzip -9 > %s' % filename)
    time.sleep(1)
    return send_file(filename)


  @app.route('/reindex')
  def reindex():
    """ 
    Starts the prune process which cleans up and offloads audio files but also re-index 
    the database.

    This is useful in the cases where bugs have led to improper registration of the 
    streams and a busted building of the database.  It's fairly expensive in I/O costs 
    so this shouldn't be done as the default.
    """
    cloud.prune(reindex=True)
    return success("Reindexing started")

  @app.route('/prune')
  def prune():
    """ 
    Starts the prune sub-process which cleans up and offloads audio files 
    following the rules outlined in the configuration file (viewable with the stats call)
    """
    cloud.prune(force=True)
    return success("Pruning started")


  @app.route('/slices/<time>/<name>')
  def send_named_stream(time, name):
    """
    Similar to the /slices/path endpoint, this end point sends a stream that is at time <time> with
    name <name>.
    """
    return send_stream(time, download_name=name)

  @app.route('/slices/<path:path>')
  def send_stream(path, download_name=None):
    """
    Downloads a stream from the server. The path is callsign-date_duration.mp3

      * callsign: The callsign returned by /stats
      * date: in the format YYYYMMDDHHMM such as 201508011005 for 
        2015-08-01 10:05
      * duration: A value, in minutes, to return.

    The mp3 extension should be used regardless of the actual format of the stream -
    although the audio returned will be in the streams' native format.
    
    The streams are created and sent on-demand, so there may be a slight delay before
    it starts.
    """
    base_dir = "%s%s/" % (config['storage'], misc.DIR_SLICES)

    if not path.startswith(config['callsign']):
      path = "%s-%s" % (config['callsign'], path)

    if not path.endswith('.mp3'):
      path = "%s.mp3" % path

    file_name = base_dir + path

    # If the file doesn't exist, then we need to slice it and create it based on our query.
    if not os.path.isfile(file_name):
      cloud.register_stream_list()

      # This tells us that if it were to exist, it would be something
      # like this.
      request_info = audio.stream_info(file_name)
      logging.info(request_info)

      # we can do something rather specific here ... 
      #
      # first we get our generic stream list using our start_minute from the info.
      stream_list, episode_list = cloud.find_streams(start_list=[request_info['start_minute']], duration_min=request_info['duration_sec'] / 60.0)
      
      for ep in episode_list:
        episode = ep[0]
        first_slice = episode[0]

        if first_slice['week_number'] == request_info['week_number']:
          # This means that we've found the episode that we want
          # We will block on this.
          relative_start_minute = request_info['start_minute'] - first_slice['start_minute']

          logging.info(episode)
          audio.stitch_and_slice_process(file_list=episode, relative_start_minute=relative_start_minute, duration_minute=request_info['duration_sec'] / 60.0)

          # And break out of our loop ... now everything should exist.
          break

    return send_file_partial("%s/%s" % (base_dir, path), requested_path=path, file_name=download_name)

  @app.route('/restart')
  def restart():
    """ 
    Restarts an instance. This does so in a gapless non-overlapping way.
    """
    misc.shutdown(do_restart=True)
    return success("restarting...")


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

    if newversion != misc.__version__:
      os.system('pip install --user -r requirements.txt') 

      # from http://blog.petrzemek.net/2014/03/23/restarting-a-python-script-within-itself/
      misc.shutdown(do_restart=True)
      return success("Upgrading from %s to %s" % (misc.__version__, newversion))

    os.chdir(cwd)
    return success('Version %s is current' % misc.__version__)


  @app.route('/heartbeat')
  def heartbeat():
    """
    A low resource version of the /stats call ... this is invoked
    by the server health check.  Only the vitals are reported.
    
    It helps us see if disk space is going nuts or if we aren't recording
    right now.
    
    This allows us to check if a restart happened between invocations.
    """
    return jsonify(misc.base_stats()), 200


  @app.route('/stats')
  def stats():
    """ 
    Reports various statistical metrics on a particular server.  
    Use this with the graph.py tool to see station coverage.
    """
    misc.am_i_official()
    db = DB.connect()

    stats = misc.base_stats()

    stats.update({
      'intents': DB.all('intents'),
      'hits': db['c'].execute('select sum(read_count) from intents').fetchone()[0],
      'kv': DB.all('kv'),
      'uptime': TS.uptime(),
      'pwd': os.getcwd(),
      'free': os.popen("df -h / | tail -1").read().strip(),
      # Reporting the list as fractional GB is more useful.
      'streams': DB.all('streams', sort_by='start_unix'),
      'config': misc.public_config()
    })

    return jsonify(stats), 200
  

  # Using http://flask.pocoo.org/docs/0.10/patterns/streaming/ as a reference.
  @app.route('/live/<start>')
  def live(start, offset_min=0):
    """ 
    Sends off a live-stream equivalent.  Two formats are supported:

     * duration - In the form of strings such as "1pm" or "2:30pm"
     * offset - starting with a negative "-", this means "from the present".
        For instance, to start the stream from 5 minutes ago, you can do "-5"

    """
    if start[0] == '-' or start.endswith('min'):
      # dump things like min or m
      start = re.sub('[a-z]', '', start)
      return redirect('/live/m%f' % (float(TS.minute_now() - abs(float(start)))), code=302)

    # The start is expressed in times like "11:59am ..." We utilize the
    # library we wrote for streaming to get the minute of day this is.
    if start[0] == 'm':
      requested_minute = float(start[1:]) % TS.ONE_DAY_MINUTE 

    else:
      candidate = start
      requested_minute = TS.to_utc('mon', candidate) - offset_min

    offset_sec = 0
    range_header = request.headers.get('Range', None)
    if range_header:
      m = re.search('(\d+)-', range_header)
      g = m.groups()
      if g[0]: 
        byte1 = int(g[0])

        # We use the byte to compute the offset
        offset_sec = float(byte1) / ((int(DB.get('bitrate')) or 128) * (1000 / 8.0))
    

    #print "--- REQUEST @ ", start, range_header, offset_sec
    current_minute = TS.minute_now() % TS.ONE_DAY_MINUTE

    now_time = TS.now()
    requested_time = now_time - timedelta(minutes=current_minute) + timedelta(minutes=requested_minute)

    # print requested_time, now_time, requested_minute, current_minute
    # If the requested minute is greater than the current one, then we can presume that
    # the requested minute refers to yesterday ... as in, someone wants 11pm
    # and now it's 1am.
    if requested_minute > current_minute:
      requested_time -= timedelta(days=1)

    # It's important to do this AFTER the operation above otherwise we wrap around to yesterday
    requested_time += timedelta(seconds=offset_sec)

    # Get the info for the file that contains this timestamp
    start_info, requested_time_available = cloud.get_file_for_ts(target_time=requested_time, bias=-1)
    requested_time = max(requested_time, requested_time_available)
    start_second = (requested_time - start_info['start_date']).total_seconds()

    response = Response(audio.list_slice_stream(start_info, start_second), mimetype=audio.our_mime())

    return response


  @app.route('/at/<start>/<duration_string>')
  def at(start, duration_string='1hr'):
    """
    Sends a stream using a human-readable (and human-writable) definition 
    at start time.  This uses the dateutils.parser library and so strings 
    such as "Monday 2pm" are accepted.

    Because the space, 0x20 is such a pain in HTTP, you can use "_", 
    "-" or "+" to signify it.  For instance,

        /at/monday_2pm/1hr

    Will work fine
    """
    dt = TS.str_to_time(start)
    duration_min = TS.duration_parse(duration_string)
    endpoint = '%s-%s_%d.mp3' % (misc.config['callsign'], TS.ts_to_name(dt), duration_min)
    return send_stream(endpoint, download_name=endpoint)

  @app.route('/<weekday>/<start>/<duration_string>')
  def at_method2(weekday, start, duration_string):
    """
    This is identical to the stream syntax, but instead it is similar to
    /at ... it uses the same notation but instead returns an audio file
    directly.

    You must specify a single weekday ... I know, total bummer.
    """
    weekday_map = {
      'mon': 'monday', 
      'tue': 'tuesday',
      'wed': 'wednesday',
      'thu': 'thursday', 
      'fri': 'friday', 
      'sat': 'saturday', 
      'sun': 'sunday'
    }

    # The alternative form for this is something like
    # /tuesday_8pm/1hr/showname.xml
    if duration_string.count('.') > 0:
      dt = TS.str_to_time(weekday)

      # order is a little incompatible.
      return stream(weekday=TS.to_minute(dt), start=None, duration_string=start, showname=duration_string)


    if weekday not in weekday_map:
      return "The first parameter, %s, is not a recognized weekday." % weekday

    return at("%s_%s" % (weekday_map[weekday], start), duration_string)
    

  @app.route('/<weekday>/<start>/<duration_string>/<showname>')
  def stream(weekday, start, duration_string, showname):
    """
    Returns a podcast, m3u, or pls file based on the weekday, start and duration.
    This is designed to be read by podcasting software such as podkicker, 
    itunes, and feedburner.

    weekdays are defined as mon, tue, wed, thu, fri, sat, sun.

    If a show occurs multiple times per week, this can be specified with
    a comma.  for instance,

    /mon,tue,fri/4pm/1hr
    
    The showname should be followed by an xml, pls, or m3u extension.

    It should also be viewable in a modern web browser.

    If you can find a podcaster that's not supported, please send an email 
    to indycast@googlegroups.com.
    """
    
    if isinstance(weekday, (float)):
      start_time_list = [weekday]
      weekday_list = [ TS.WEEKDAY_LIST[ int(weekday / (60 * 24)) ] ]

    else:
      # Supports multiple weekdays
      weekday_list = weekday.split(',')
      start_time_list = [TS.to_utc(day, start) for day in weekday_list]

    duration_min = TS.duration_parse(duration_string)

    # This means we failed to parse
    if not duration_min:
      return server.do_error("duration '%s' is not set correctly" % duration_string)

    if not isinstance(start_time_list[0], (int, long, float)):
      return server.do_error('weekday and start times are not set correctly')

    # In #22 We're going to add 2 minutes to the duration to make sure that we get
    # the entire episode.
    duration_min += 2

    # And according to #149 we also go a minute back for the start time ... 
    # we need to do a little math to make sure we don't get a -1 edge case
    start_time_list = [(TS.MINUTES_PER_WEEK + offset - 1) % TS.MINUTES_PER_WEEK for offset in start_time_list]

    # If we are here then it looks like our input is probably good.
    
    # Strip the .xml from the showname ... this will be used in our xml.
    file_type = showname[-3:]
    showname = showname[:-4]

    # We come in with spaces as underscores so here we translate that back
    showname = re.sub('_', ' ', showname)

    # This will register the intent if needed for future recordings
    # (that is if we are in ondemand mode)
    DB.register_intent(start_time_list, duration_min)

    # Make sure that we have all of our streams registered before trying
    # to infer what we can send to the user.
    cloud.register_stream_list()

    # Look for streams that we have which match this query and duration.
    # This will also create slices if necessary in a sub process.
    # The list of files that returns will include this not-yet-created
    # file-name as essentially a "promise" to when it will be made.
    feed_list = cloud.find_and_make_slices(start_time_list, duration_min)
    # print feed_list

    # Then, taking those two things, make a feed list from them.
    return server.generate_feed(
      file_type=file_type,
      showname=showname, 
      feed_list=feed_list, 
      duration_min=duration_min, 
      weekday_list=weekday_list, 
      start=start, 
      duration_string=duration_string
    )


  if __name__ == '__main__':
    pid = misc.change_proc_name("%s-webserver" % config['callsign'])

    signal.signal(signal.SIGUSR1, webserver_shutdown)
    # When we do an upgrade or a restart, there's a race condition of getting to start this server
    # before the previous one has cleaned up all the socket work.  So if the time is under our
    # patience threshold then we sleep a second and just try again, hoping that it will work.
    patience = misc.PROCESS_DELAY * 2
    attempt = 1

    start = TS.unixtime('delay')
    while TS.unixtime('delay') - start < (patience + 3):
      try:
        print "Listening on %s" % config['port']
        app.logger.addHandler(logging.getLogger())
        app.run(threaded=True, port=config['port'], host='0.0.0.0')
        break

      except Exception as exc:
        if TS.unixtime('delay') - start < patience:
          print "[attempt: %d] Error, can't start server ... perhaps %s is already in use?" % (attempt, config['port'])
          attempt += 1
          time.sleep(misc.PROCESS_DELAY / 4)

        elif TS.unixtime('delay') - start < (patience + 4):
          pid=os.popen("netstat -anlp | grep :%s | awk ' { print $NF }' | sed 's/\/.*//'" % config['port']).read().strip().split('\n')[0]

          try:
            pid_numeric = int(pid)
            print "Fuck it, I'm killing %s." % pid
            os.kill(pid_numeric)

          except:
            pass

          time.sleep(misc.PROCESS_DELAY / 4)

def stream_download(callsign, url, my_pid, file_name):
  # Curl interfacing which downloads the stream to disk. 
  # Follows redirects and parses out basic m3u.
  pid = misc.change_proc_name("%s-download" % callsign)

  nl = {'stream': None, 'curl_handle': None}

  def dl_stop(signal, frame):
    sys.exit(0)

  def cback(data): 

    if not misc.params['shutdown_time']:
      if not misc.download_ipc.empty():
        what, value = misc.download_ipc.get(False)
        if what == 'shutdown_time':
          misc.params['shutdown_time'] = value

    elif TS.unixtime('dl') > misc.params['shutdown_time']:
      sys.exit(0)

    if misc.params['isFirst'] == True:
      misc.params['isFirst'] = False

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
    misc.queue.put(('heartbeat', (TS.unixtime('hb'), len(data))))

    if not nl['stream']:
      try:
        nl['stream'] = open(file_name, 'w')

      except Exception as exc:
        logging.critical("Unable to open %s. Can't record. Must exit." % file_name)
        sys.exit(-1)

    nl['stream'].write(data)

    if not misc.manager_is_running():
      misc.shutdown()

  # signal.signal(signal.SIGTERM, dl_stop)
  misc.params['isFirst'] = True
  curl_handle = pycurl.Curl()
  curl_handle.setopt(curl_handle.URL, url)
  curl_handle.setopt(pycurl.WRITEFUNCTION, cback)
  curl_handle.setopt(pycurl.FOLLOWLOCATION, True)
  nl['curl_handle'] = curl_handle

  try:
    curl_handle.perform()

  except TypeError as exc:
    logging.info("Properly shutting down.")

  except Exception as exc:
    logging.warning("Couldn't resolve or connect to %s." % url)

  curl_handle.close()

  if nl['stream'] and type(nl['stream']) != bool:
    nl['stream'].close()
    # This is where we are sure of the stats on this file, because
    # we just closed it ... so we can register it here.
    info = audio.stream_info(file_name)

    DB.register_stream(info)


def my_process_shutdown(process):
  # A small function to simplify the logic below. 
  if process and process.is_alive():
    logging.info("[%s:%d] Shutting down" % ('download', process.pid))
    process.terminate()

  return None


def stream_manager():
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
  first_time = 0
  total_bytes = 0
  normalize_delay = 6

  cascade_time = misc.config['cascadetime']
  cascade_buffer = misc.config['cascadebuffer']
  cascade_margin = cascade_time - cascade_buffer

  last_prune = 0
  last_success = 0

  change_state = None
  SHUTDOWN = 1
  RESTART = 2
  shutdown_time = None
  misc.download_ipc = Queue()

  # Number of seconds to be cycling
  cycle_time = misc.config['cycletime']

  process = None
  process_next = None

  # The manager will be the one that starts this.
  misc.pid_map['webserver'] = Process(target=server_manager, args=(misc.config,))
  misc.pid_map['webserver'].start()

  file_name = None

  # A wrapper function to start a donwnload process
  def download_start(file_name):
    """ Starts a process that manages the downloading of a stream. """
    global g_download_pid

    g_download_pid += 1
    logging.info("Starting cascaded downloader #%d. Next up in %ds" % (g_download_pid, cascade_margin))

    #
    # There may be a multi-second lapse time from the naming of the file to
    # the actual start of the download so we should err on that side by putting it
    # in the future by some margin
    #
    file_name = '%s/%s-%s.mp3' % (misc.DIR_STREAMS, callsign, TS.ts_to_name(TS.now(offset_sec=misc.PROCESS_DELAY / 2)))
    process = Process(target=stream_download, args=(callsign, misc.config['stream'], g_download_pid, file_name))
    process.start()
    return [file_name, process]


  # see https://github.com/kristopolous/DRR/issues/91:
  # Randomize prune to offload disk peaks
  prune_duration = misc.config['pruneevery'] + (1 / 8.0 - random.random() / 4.0)

  while True:
    #
    # We cycle this to off for every run. By the time we go throug the queue so long 
    # as we aren't supposed to be shutting down, this should be toggled to true.
    #
    flag = False

    if last_prune < (TS.unixtime('prune') - TS.ONE_DAY_SECOND * prune_duration):
      prune_duration = misc.config['pruneevery'] + (1 / 8.0 - random.random() / 4.0)
      # We just assume it can do its business in under a day
      misc.pid_map['prune'] = cloud.prune()
      last_prune = TS.unixtime('prune')

    TS.get_offset()

    lr_set = False
    while not misc.queue.empty():
      flag = True
      what, value = misc.queue.get(False)

      # The curl proces discovered a new stream to be
      # used instead.
      if what == 'stream':
        misc.config['stream'] = value
        logging.info("Using %s as the stream now" % value)
        # We now don't toggle to flag in order to shutdown the
        # old process and start a new one

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
          logging.info("Restart requested ... shutting down downloader at %s" % TS.ts_to_name(shutdown_time, with_seconds=True))

          time.sleep(12)
          #logging.info(DB.get('runcount', use_cache=False))
          ps_out = int(os.popen('ps axf | grep [%c]%s | grep python | wc -l' % (misc.config['callsign'][0], misc.config['callsign'][1:]) ).read().strip())

          if ps_out > 0: 
            logging.info("Found %d potential candidates (need at least 1)" % ps_out)
            # This makes it a restricted soft shutdown
            misc.shutdown_real(do_restart=True)
            misc.download_ipc.put(('shutdown_time', shutdown_time))

          else:
            logging.warn("Couldn't find a replacement process ... not going anywhere.");

      elif what == 'heartbeat':
        if not lr_set and value[1] > 100:
          lr_set = True
          DB.set('last_recorded', time.time())

        if not has_bitrate: 

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
            total_bytes += value[1]

            # We still give it a time period after the normalizing delay in order to build enough
            # samples to make a solid guess at what this number should be.
            if (value[0] - first_time > (normalize_delay + 60)):
              # We take the total bytes, calculate it over our time, in this case, 25 seconds.
              est = total_bytes / (value[0] - first_time - normalize_delay)

              # We find the nearest 8Kb increment this matches and then scale out.
              # Then we multiply out by 8 (for _K_ B) and 8 again for K _b_.
              bitrate = int( round (est / 1000) * 8 )
              DB.set('bitrate', bitrate)

    # Check for our management process
    if not misc.manager_is_running():
      logging.info("Manager isn't running");
      change_state = SHUTDOWN

    # The only way for the bool to be toggled off is if we are not in full-mode ... 
    # we get here if we should NOT be recording.  So we make sure we aren't.
    if change_state == SHUTDOWN or (change_state == RESTART and TS.unixtime('dl') > shutdown_time):
      process = my_process_shutdown(process)
      process_next = my_process_shutdown(process_next)
      misc.shutdown_real()

    else:
      # Didn't respond in cycle_time seconds so kill it
      if not flag:
        process = my_process_shutdown(process)

      if not process and not change_state:
        file_name, process = download_start(file_name)
        last_success = TS.unixtime('dl')

      # If we've hit the time when we ought to cascade
      elif TS.unixtime('dl') - last_success > cascade_margin:

        # And we haven't created the next process yet, then we start it now.
        if not process_next:
          file_name, process_next = download_start(file_name)

      # If our last_success stream was more than cascade_time - cascade_buffer
      # then we start our process_next
      
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
    if not change_state and TS.unixtime('dl') - last_success > cascade_time and process:
      logging.info("Stopping cascaded downloader")
      process.terminate()

      # If the process_next is running then we move our last_success forward to the present
      last_success = TS.unixtime('dl')

      # we rename our process_next AS OUR process
      process = process_next

      # and then clear out the old process_next pointer
      process_next = None

    # Increment the amount of time this has been running
    DB.incr('uptime', cycle_time)

    time.sleep(cycle_time)

def read_config(config):
  import ConfigParser
  # Reads a configuration file. 
  # Currently documented at https://github.com/kristopolous/DRR/wiki/Join-the-Federation
  Config = ConfigParser.ConfigParser()
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

    # The (day) time to expire an intent to record
    'expireafter': 45,

    # The time to prolong a download to make sure that 
    # a restart or upgrade is seamless, in seconds.
    'restart_overlap': 15,

    # The TCP port to run the server on
    'port': 5000,

    # The (day) duration we should be archiving things.
    'archivedays': 28,

    # The (second) time in looking to see if our stream is running
    'cycletime': 7,

    # The (second) time to start a stream BEFORE the lapse of the cascade-time
    'cascadebuffer': 15,

    # The (second) time between cascaded streams
    'cascadetime': 60 * 15,

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
    'cloudarchive': 1.20,
    
    # Run the pruning every this many days (float)
    'pruneevery': 0.5
  }

  for k, v in defaults.items():
    if k not in misc.config:
      misc.config[k] = v
    else:
      if type(v) is int: misc.config[k] = int(misc.config[k])
      elif type(v) is long: misc.config[k] = long(misc.config[k])
      elif type(v) is float: misc.config[k] = float(misc.config[k])

  # In case someone is specifying ~/radio 
  misc.config['storage'] = os.path.expanduser(misc.config['storage'])
  misc.config['_private'] = {}

  if misc.config['cloud']:
    misc.config['cloud'] = os.path.expanduser(misc.config['cloud'])

    if os.path.exists(misc.config['cloud']):
      # If there's a cloud conifiguration file then we read that too
      cloud_config = ConfigParser.ConfigParser()
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
  formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y%m%d_%H%M_%S')
  handler = RotatingFileHandler('indycast.log', maxBytes=2000000, backupCount=5)
  handler.setFormatter(formatter)
  handler.setLevel(numeric_level)
  logger.setLevel(numeric_level)
  logger.addHandler(handler)

  # Increment the number of times this has been run so we can track the stability of remote 
  # servers and instances.
  DB.upgrade()
  DB.incr('runcount')

  # This is how we discover if we are the official server or not.
  # Look at the /uuid endpoint to see how this magic works.
  misc.config['uuid'] = os.popen('uuidgen').read().strip()

  signal.signal(signal.SIGINT, misc.shutdown_handler)
  signal.signal(signal.SIGUSR1, misc.shutdown_handler)
  signal.signal(signal.SIGHUP, misc.do_nothing)


if __name__ == "__main__":
  # From http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice

  if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    server_manager(misc.config)

  else: 
    # Ignore all test scaffolding
    misc.IS_TEST = False
    misc.start_time = TS.unixtime()

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="./indy_config.txt", help="Configuration file (default ./indy_config.txt)")
    parser.add_argument('--version', action='version', version='indycast %s :: Aug 2015' % misc.__version__)
    parser.add_argument("--daemon", action='store_true',  help="run as daemon")
    args = parser.parse_args()
    if args.daemon:
      Popen( filter(lambda x: x != '--daemon', sys.argv) )
      sys.exit(0)

    read_config(args.config)      

    pid = misc.change_proc_name("%s-manager" % misc.config['callsign'])

    # This is the pid that should be killed to shut the system
    # down.
    misc.manager_is_running(pid)
    with open(misc.PIDFILE_MANAGER, 'w+') as f:
      f.write(str(pid))

    stream_manager()
