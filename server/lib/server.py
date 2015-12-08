#!/usr/bin/python 
import logging, re
import misc 
from cloud import get_size
import signal
import lxml.etree as ET
import time
import os
from datetime import timedelta, date

import lib.ts as TS
import lib.db as DB
import lib.audio as audio
import lib.cloud as cloud

from flask import Flask, request, jsonify, Response, url_for, redirect, send_file
from urllib import quote

def do_error(errstr):
  # Returns a server error as a JSON result. 
  return jsonify({'result': False, 'error':errstr}), 500
    
def generate_feed(file_type, **kwargs):
  # Take the file extension that the user supplied and then try to return
  # a feed based on it
  if file_type == 'pls': 
    payload = generate_pls(**kwargs)
    mime = 'audio/x-scpls'

  elif file_type == 'm3u': 
    payload = generate_m3u(**kwargs)
    mime = 'audio/x-mpegurl'

  # If we fail to find one, we revert to xml
  else: 
    payload = generate_xml(**kwargs)
    mime = 'text/xml'

  return Response(payload, mimetype=mime )


def generate_m3u(showname, feed_list, duration_min, weekday_list, start, duration_string):
  payload = ['#EXTM3U']
  base_url = 'http://indycast.net/%s/' % (misc.config['callsign'], )

  for feed in reversed(feed_list):
    link = "%s%s" % (base_url, feed['name'])
    payload.append('#EXTINF:%d,%s - %s' % (duration_min, showname, feed['start_date'].strftime("%Y.%m.%d")))
    payload.append(link)

  return "\n".join(payload)


def generate_pls(showname, feed_list, duration_min, weekday_list, start, duration_string):
  payload = ["[playlist]", "NumberOfEntries=%d" % len(feed_list)]
  base_url = 'http://indycast.net/%s/' % (misc.config['callsign'], )

  stream_number = 1
  # Show the most recent feeds first
  for feed in reversed(feed_list):
    link = "%s%s" % (base_url, feed['name'])
    payload.append('Title%d=%s - %s' % (stream_number, showname, feed['start_date'].strftime("%Y.%m.%d")))
    payload.append('File%d=%s' % (stream_number, link, ))
    stream_number += 1

  return "\n".join(payload)


def generate_xml(showname, feed_list, duration_min, weekday_list, start, duration_string):
  # It obviously returns an xml file ... I mean duh.
  # In the xml file we will lie about the duration to make life easier
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

  base_url = 'http://indycast.net/%s/' % (misc.config['callsign'], )
  callsign = misc.config['callsign']

  nsmap = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'media': 'http://search.yahoo.com/mrss/', 
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'feedburner': 'http://rssnamespace.org/feedburner/ext/1.0'
  }

  root = ET.Element('rss', nsmap=nsmap)
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
  itunes_image.attrib['href'] = 'http://indycast.net/icon/%s_1400.png' % quote(showname)

  media_image = ET.SubElement(channel, '{%s}thumbnail' % nsmap['media'])
  media_image.attrib['url'] = 'http://indycast.net/icon/%s_1400.png' % quote(showname)

  image = ET.SubElement(channel, 'image')
  for k,v in {
    'url': 'http://indycast.net/icon/%s_200.png' % quote(showname),
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
      itunes_duration = "%d:%s" % (int(duration_min / 60.0), itunes_duration)    

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
    content.attrib['fileSize'] = str(get_size(file_name))
    content.attrib['type'] = 'audio/mpeg'

    # The length of the audio we will just take as the duration
    content = ET.SubElement(item, 'enclosure')
    content.attrib['url'] = link
    content.attrib['length'] = str(get_size(file_name))
    content.attrib['type'] = 'audio/mpeg'

  tree = ET.ElementTree(root)

  return ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8")

def manager(config):
  # Main flask process that manages the end points. 
  app = Flask(__name__)

  def webserver_shutdown(signal=15, frame=None):
    title = SP.getproctitle()
    logging.info('[%s:%d] Shutting down' % (title, os.getpid()))
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
      return 'File %s not found. Perhaps the stream is old?' % requested_path, 404

    range_header = request.headers.get('Range', None)
    if not range_header: 
      with open(path, 'rb') as f:
        data = f.read()

      rv = Response( data, 200, mimetype=audio.our_mime(), direct_passthrough=True )
      if not file_name:
        file_name = os.path.basename(path)
        
      rv.headers.add('Content-Disposition', 'attachment; filename="%s"' % file_name)
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


  @app.route('/rename')
  def rename():
    return cloud.rename()

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
    return success('Reindexing...')

  @app.route('/prune')
  def prune():
    """ 
    Starts the prune sub-process which cleans up and offloads audio files 
    following the rules outlined in the configuration file (viewable with the stats call)
    """
    cloud.prune(force=True)
    return success('Pruning...')


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
    DB.incr('hits-dl')
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
    return success('restarting...')


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
    DB.incr('hits-live')
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
      return 'The first parameter, %s, is not a recognized weekday.' % weekday

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
      return do_error("duration '%s' is not set correctly" % duration_string)

    if not isinstance(start_time_list[0], (int, long, float)):
      return do_error('weekday and start times are not set correctly')

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
    return generate_feed(
      file_type=file_type,
      showname=showname, 
      feed_list=feed_list, 
      duration_min=duration_min, 
      weekday_list=weekday_list, 
      start=start, 
      duration_string=duration_string
    )


  print __name__
  if __name__ == 'lib.server':
    # When we do an upgrade or a restart, there's a race condition of getting to start this server
    # before the previous one has cleaned up all the socket work.  So if the time is under our
    # patience threshold then we sleep a second and just try again, hoping that it will work.
    patience = misc.PROCESS_DELAY * 2
    attempt = 1

    start = TS.unixtime('delay')
    while TS.unixtime('delay') - start < (patience + 3):
      try:
        print 'Listening on %s' % config['port']
        app.logger.addHandler(logging.getLogger())
        app.run(threaded=True, port=config['port'], host='0.0.0.0')
        break

      except Exception as exc:
        if TS.unixtime('delay') - start < patience:
          print '[attempt: %d] Error, can not start server ... perhaps %s is already in use?' % (attempt, config['port'])
          attempt += 1
          time.sleep(misc.PROCESS_DELAY / 4)

        elif TS.unixtime('delay') - start < (patience + 4):
          pid = os.popen("netstat -anlp | grep :%s | awk ' { print $NF }' | sed 's/\/.*//'" % config['port']).read().strip().split('\n')[0]

          try:
            pid_numeric = int(pid)
            print "Fuck it, I'm killing %s." % pid
            os.kill(pid_numeric)

          except:
            pass

          time.sleep(misc.PROCESS_DELAY / 4)
