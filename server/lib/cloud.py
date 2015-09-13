#!/usr/bin/python -O
import os
import re
import time 
import logging
import misc 
import lib.db as DB
import lib.ts as TS
import audio
from sets import Set
from glob import glob
from datetime import datetime, timedelta, date
from multiprocessing import Process, Queue

def size(basedir):
  total = 0

  for basename in os.listdir(basedir):
    
    path = "%s/%s" % (basedir, basename)

    if os.path.isdir(path):
      total += size(path)

    elif os.path.isfile(path):
      total += os.path.getsize(path)

  return total


def get(path, do_open=True):
  """
  If the file exists locally then we return it, otherwise
  we go out to the network store and retrieve it.
  """
  # Let's make sure it exists and isn't some nonsense size
  # Which I've arbitrary set as a few thousand bytes
  if os.path.exists(path) and os.path.getsize(path) > 3000:
    if do_open: return open(path, 'rb')
    return True

  else:
    res = download(path)
    if res:
      if do_open: return open(path, 'rb')
      return True

  return None


def connect(config=False):
  """ Connect to the cloud service. """
  if not config: config = misc.config['_private']

  from azure.storage import BlobService
  container = 'streams'

  if not 'azure' in config:
    return None, None

  blob_service = BlobService(config['azure']['storage_account_name'], config['azure']['primary_access_key'])
  blob_service.create_container(container, x_ms_blob_public_access='container')
  return blob_service, container


def unlink(path, config=False):
  """ Remove a file from the cloud service. """
  fname = os.path.basename(path)
  blob_service, container = connect(config)

  try:
    blob_service.delete_blob(container, fname)
    logging.debug("Prune[cloud]: Deleted %s" % fname)

  except:
    logging.warn("Prune[cloud]: Failed to delete %s" % fname)

  return None


def put(path):
  """ Place a file, given a path, in the cloud. """
  if not misc.am_i_official():
    logging.info ("I would have uploaded %s but I'm not the official %s server" % (path, misc.config['callsign']) )
    return False

  blob_service, container = connect()

  if blob_service:
    try:
      res = blob_service.put_block_blob_from_path(
        container,
        os.path.basename(path),
        path,
        max_connections=5,
      )
      return True

    except:
      logging.debug('Unable to put %s in the cloud.' % path)

  return False


def register_stream_list(reindex=False):
  """ Find the local streams and make sure they are all registered in the sqlite3 database. """
  #
  # Get the existing streams as a set
  #
  # If we are asked to re-index (due to trying to fix a bug) then we ignore what we have
  # and just go ahead and do everything.
  #
  if reindex:
    all_registered = Set([])

  else: 
    all_registered = Set(DB.all('streams', ['name']))

  # There should be a smarter way to do this ... you'd think. We should also
  # be more faithfully giving things extensions since it's not 100% mp3
  all_files = Set(glob('%s/*.mp3' % misc.DIR_STREAMS))
 
  diff = all_files.difference(all_registered)

  # This is a list of files we haven't scanned yet...
  if not diff: return True

  # This basically means we could still be writing
  # this file.
  #
  # We take the cascade time and then buffer it by a minute, just
  # to be sure.
  # 
  # If the creation time is less then this then we don't register this
  # until later.
  cutoff = time.mktime((datetime.now() - timedelta(minutes=1, seconds=misc.config['cascadetime'])).timetuple())

  for fname in diff:
    if len(fname) == 0 or os.path.getctime(fname) > cutoff:
      next

    info = audio.stream_info(fname)
    if not info:
      continue

    DB.register_stream(info)

    if not misc.manager_is_running():
      logging.info("Manager is gone, shutting down")
      raise Exception()


def find_streams(start_list, duration_min):
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
  episode_list = []
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
    # print start, duration_min, end_search
    condition_list.append('start_minute < %d and end_minute >= %d' % (start, start))
    condition_list.append('start_minute > %d and end_minute >= %d and end_minute <= %d' % (start, start, end_search))
    condition_list.append('start_minute < %d and end_minute >= %d' % (end_search, end_search))

  condition_query = "((%s))" % ') or ('.join(condition_list)

  # see https://github.com/kristopolous/DRR/issues/50 - nah this shit is buggy
  condition_query += " and start_unix < datetime(%d, 'unixepoch', 'localtime')" % (TS.sec_now() - misc.config['cascadetime'] + 3)

  full_query = "select * from streams where %s order by week_number * 10080 + start_minute asc" % condition_query

  entry_list = DB.map(db['c'].execute(full_query).fetchall(), 'streams')

  #logging.info(full_query)
  #logging.info(entry_list)
  # print full_query, len(entry_list)
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
  # Start the creation of the audio files.
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
        fname = audio.stream_name(episode, week_start, duration_min)
        print '--name',episode[0]['name'], fname

        # We get the name that it will be and then append that
        stream_list.append(audio.stream_info(fname))

        # print offset_start, duration_min, episode
        episode_list.append((episode, offset_start, duration_min))
        break

  # print stream_list, "\nbreak\n", episode_list, "\nasfdasdf\n"
  return stream_list, episode_list


def find_and_make_slices(start_list, duration_min):
  stream_list, episode_list = find_streams(start_list, duration_min)

  #for episode, offset_start_min, duration_min in episode_list:
  #  audio.stitch_and_slice(episode, offset_start_min, duration_min)

  return stream_list


def get_file_for_ts(target_time, bias=None, exclude_path=None):
  """ 
  Given a datetime target_time, this finds the closest file either with a bias
  of +1 for after, -1 for before (or within) or no bias for the closest match.

  An exclude_path can be set to remove it from the candidates to be searched
  """
  best_before_time = None
  best_before_info = None

  best_after_time = None
  best_after_info = None

  time_to_beat = None
  current_winner = None

  #print "-----------------------"
  for candidate_path in glob('%s/*.mp3' % misc.DIR_STREAMS):
    if candidate_path == exclude_path: continue

    info_candidate = audio.stream_info(candidate_path)
    if not info_candidate or info_candidate['duration_sec'] < 10.0:
      next

    difference = info_candidate['start_date'] - target_time

    # This means we want to be strictly later
    # If our difference is before, which means we are earlier,
    # then we exclude this
    #
    # BUGBUG: There's a hole in here ... pretend there's an expansive file starting at t0 and
    # a small one at t1 where start time of t0 < t1 so t1 is the file that is selected even though
    # t0 is a better candidate.
    #
    if difference < timedelta() and (not best_before_time or difference > best_before_time):
      best_before_time = difference
      best_before_info = info_candidate

    # If we want something earlier and the start date is AFTER
    # our target time then we bail
    elif difference > timedelta() and (not best_after_time or difference < best_after_time):
      best_after_time = difference
      best_after_info = info_candidate

  # print target_time, "\n", best_before_time, best_before_info, "\n", best_after_time, best_after_info
  if bias == -1:
    # Make sure that our candidate has our time within it
    # print best_before_info['start_date'], timedelta(seconds=best_before_info['duration_sec']) , target_time
    if best_before_info['start_date'] + timedelta(seconds=best_before_info['duration_sec']) > target_time:
      # This means that we have found a valid file and we can return the successful target_time 
      # and our info
      return best_before_info, target_time

    # Otherwise that means that our best time doesn't actually have our target time!
    # So we return where we ought to start and the file we can start at
    if best_after_info:
      return best_after_info, best_after_info['start_date']

    else:
      return None, None

  if bias == None:
    if not best_after_info or (abs(best_before_time) < abs(best_after_time)):
      return best_before_info, max(target_time, best_before_info['start_date'])

    return best_after_info, min(target_time, best_after_info['start_date'])

  if bias == +1:
    # print best_after_info, best_before_info, exclude_path
    if not best_after_info:
      return None, target_time

    return best_after_info, min(target_time, best_after_info['start_date'])


def get_next(info_query):
  """ Given a file, we look to see if there's another one which could come after -- we won't look in the database """
  if type(info_query) is str:
    info_query = audio.stream_info(info_query)

  #
  # We are looking for a file with the closest start time to 
  # the end time of our stream whose file size is greater than a 
  # certain threshold
  #
  target_time = info_query['start_date'] + timedelta(seconds=info_query['duration_sec'])

  return get_file_for_ts(target_time=target_time, bias=None, exclude_path=info_query['name'])

  
def prune(reindex=False):
  """ Gets rid of files older than archivedays - cloud stores things if relevant. """

  # Now when the child calls it it won't hit the network for every prune.
  process = Process(target=prune_process, args=(misc.lockMap, reindex,))
  process.start()
  return process


def prune_process(lockMap, reindex=False):
  """ 
  This is internal, call prune() directly. This is a normally blocking
  process that is prepared by prune(), making it easily callable asynchronously 
  """
  # If another prune is running then we just bail
  if not lockMap['prune'].acquire(False):
    logging.warn("Tried to run another prune whilst one is running. Aborting")
    return True

  # If we are the first process then we need to make sure that the webserver is up before
  # we do this to check to see if we are official
  time.sleep(2)

  pid = misc.change_proc_name("%s-cleanup" % misc.config['callsign'])

  # We want to run the am_i_official here since it could block on a DNS lookup
  misc.am_i_official()

  try:
    register_stream_list(reindex)

  except:
    return None

  db = DB.connect()

  archive_duration = misc.config['archivedays'] * TS.ONE_DAY_SECOND
  cutoff = TS.unixtime('prune') - archive_duration

  # Remove all slices older than 4 hours.
  slice_cutoff = TS.unixtime('prune') - 0.1667 * TS.ONE_DAY_SECOND

  cloud_cutoff = None
  if misc.config['cloud']:
    cloud_cutoff = TS.unixtime('prune') - misc.config['cloudarchive'] * TS.ONE_DAY_SECOND

  # Put thingies into the cloud.
  count = 0
  for file_name in glob('*/*.mp3'):
    #
    # Depending on many factors this could be running for hours
    # or even days.  We want to make sure this isn't a blarrrghhh
    # zombie process or worse yet, still running and competing with
    # other instances of itself.
    #
    if not misc.manager_is_running():
      return None

    ctime = os.path.getctime(file_name)

    # print "Looking at ", file_name, ctime, cutoff, archive_duration,  misc.config['archivedays'], misc.am_i_official()
    # We observe the rules set up in the config.
    if file_name.startswith('slices') and ctime < slice_cutoff or ctime < cutoff:
      logging.debug("Prune[remove]: %s" % file_name)
      os.unlink(file_name)
      count += 1 

    # We want to make sure we aren't archiving the slices
    elif cloud_cutoff and ctime < cloud_cutoff and not file_name.startswith('slice') and misc.am_i_official():
      logging.debug("Prune[cloud]: %s" % file_name)

      # Only unlink the file if I can successfully put it into the cloud.
      if put(file_name):
        try:
          os.unlink(file_name)

        except:
          logging.debug("Prune[cloud]: Couldn't remove %s" % file_name)

  for file_name in glob('%s/*.gz' % misc.DIR_BACKUPS):
    ctime = os.path.getctime(file_name)

    # We observe the rules set up in the config.
    if ctime < cutoff:
      logging.debug("Prune: %s" % file_name)
      os.unlink(file_name)
      count += 1 

  # The map names are different since there may or may not be a corresponding
  # cloud thingie associated with it.
  db = DB.connect()

  unlink_list = db['c'].execute('select name, id from streams where end_unix < date("now", "-%d seconds") or end_minute - start_minute < 0.05' % archive_duration).fetchall()

  for file_name_tuple in unlink_list:
    file_name = str(file_name_tuple[0])
    id = file_name_tuple[1]

    logging.debug("Prune[remove]: %s" % file_name)
    # If there's a cloud account at all then we need to unlink the 
    # equivalent mp3 file
    if cloud_cutoff and misc.am_i_official():
      "cloud.";unlink(file_name)

      # After we remove these streams then we delete them from the db.
      db['c'].execute('delete from streams where id = %d' % id)
      db['conn'].commit()

    # now only after we've deleted from the cloud can we delete the local file
    if os.path.exists(file_name):
      os.unlink(file_name)
      count += 1


  logging.info("Found %d files older than %s days." % (count, misc.config['archivedays']))
  lockMap['prune'].release()


def get_size(fname):
  """ Gets a file size or just plain guesses it if it doesn't exist yet. """
  if os.path.exists(fname):
    return os.path.getsize(fname)

  # Otherwise we try to parse the magical file which doesn't exist yet.
  ts_re_duration = re.compile('_(\d*).{4}')
  ts = ts_re_duration.findall(fname)

  if len(ts):
    duration_min = int(ts[0])

    bitrate = int(DB.get('bitrate') or 128)

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

 
def download(path):
  """ Download a file from the cloud and put it in a serviceable place. """
  blob_service, container = connect()

  if blob_service:
    import azure

    fname = os.path.basename(path)
    try:
      blob_service.get_blob_to_path(
        container,
        fname,
        '%s/%s' % (misc.DIR_STREAMS, fname),
        max_connections=8,
      )
      return True

    except azure.WindowsAzureMissingResourceError as e:
      logging.debug('Unable to retreive %s from the cloud. It is not there' % fname)

      # TODO: This is a pretty deep (and probably wrong) place to do this.
      DB.unregister_stream(path)

    except Exception as e:
      logging.debug('Unable to retreive %s from the cloud.' % path)

  return False

