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

  return False


def connect(config=False):
  """ Connect to the cloud service. """
  if not config: config = misc.config['_private']

  from azure.storage import BlobService
  container = 'streams'

  blob_service = BlobService(config['azure']['storage_account_name'], config['azure']['primary_access_key'])
  blob_service.create_container(container, x_ms_blob_public_access='container')
  return blob_service, container


def unlink(path, config=False):
  """ Remove a file from the cloud service. """
  fname = os.path.basename(path)
  blob_service, container = connect(config)
  return blob_service.delete_blob(container, path)


def put(path):
  """ Place a file, given a path, in the cloud. """
  if 'test' in misc.config['_private']['azure']:
    logging.info ("I would have uploaded %s but I'm in test mode" % path)
    return False

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


def register_streams(reindex=False):
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

    DB.register_stream(
      name=fname,
      week_number=info['week'],
      start_minute=float(info['start_minute']),
      end_minute=float(info['end_minute']),
      start_unix=info['start_date'],
      end_unix=info['start_date'] + timedelta(seconds=info['duration_sec'])
    )

    if not misc.manager_is_running():
      print "Manager is gone, shutting down"
      misc.shutdown()


def get_next(path):
  """ Given a file, we look to see if there's another one which could come after """

  
def prune(reindex=False):
  """ Gets rid of files older than archivedays - cloud stores things if relevant. """

  # We want to run the am_i_official so that the thread that keeps forking the prune
  # process bequeths a cached version of whether it is official or not.
  misc.am_i_official()

  # Now when the child calls it it won't hit the network for every prune.
  pid = Process(target=prune_process, args=(misc.lockMap, reindex,))
  pid.start()
  return pid


def prune_process(lockMap, reindex=False):
  """ 
  This is internal, call prune() directly. This is a normally blocking
  process that is prepared by prune(), making it easily callable asynchronously 
  """
  # If another prune is running then we just bail
  if not lockMap['prune'].acquire(False):
    logging.warn("Tried to run another prune whilst one is running. Aborting")
    return True

  pid = misc.change_proc_name("%s-cleanup" % misc.config['callsign'])

  register_streams(reindex)
  db = DB.connect()

  archive_duration = misc.config['archivedays'] * TS.ONE_DAY
  cutoff = TS.unixtime('prune') - archive_duration

  cloud_cutoff = False
  if misc.config['cloud']:
    cloud_cutoff = TS.unixtime('prune') - misc.config['cloudarchive'] * TS.ONE_DAY

  # Put thingies into the cloud.
  count = 0
  for fname in glob('*/*.mp3'):
    #
    # Depending on many factors this could be running for hours
    # or even days.  We want to make sure this isn't a blarrrghhh
    # zombie process or worse yet, still running and competing with
    # other instances of itself.
    #
    if not misc.manager_is_running():
      misc.shutdown()

    ctime = os.path.getctime(fname)

    # We observe the rules set up in the config.
    if ctime < cutoff:
      logging.debug("Prune: %s" % fname)
      os.unlink(fname)
      count += 1 

    # We want to make sure we aren't archiving the slices
    elif cloud_cutoff and ctime < cloud_cutoff and not fname.startswith('slice'):
      logging.debug("Prune[cloud]: putting %s" % fname)

      # Only unlink the file if I can successfully put it into the cloud.
      if put(fname):
        try:
          os.unlink(fname)

        except:
          logging.debug("Prune[cloud]: Couldn't remove %s" % fname)

  for fname in glob('%s/*.gz' % misc.DIR_BACKUPS):
    ctime = os.path.getctime(fname)

    # We observe the rules set up in the config.
    if ctime < cutoff:
      logging.debug("Prune: %s" % fname)
      os.unlink(fname)
      count += 1 

  # The map names are different since there may or may not be a corresponding
  # cloud thingie associated with it.
  db = DB.connect()
  unlink_list = db['c'].execute('select name from streams where created_at < (current_timestamp - ?)', (archive_duration, )).fetchall()

  for fname in unlink_list:
    # If there's a cloud account at all then we need to unlink the 
    # equivalent mp3 file
    if cloud_cutoff:
      "cloud.";unlink(fname)

    # now only after we've deleted from the cloud can we delete the local file
    os.unlink(fname)

  # After we remove these streams then we delete them from the db.
  db['c'].execute('delete from streams where name in ("%s")' % ('","'.join(unlink_list)))
  db['conn'].commit()

  logging.info("Found %d files older than %s days." % (count, misc.config['archivedays']))
  lockMap['prune'].release()


def get_size(fname):
  """ Gets a file size or just plain guesses it if it doesn't exist yet. """
  if os.path.exists(fname):
    return os.path.getsize(fname)

  # Otherwise we try to parse the magical file which doesn't exist yet.
  ts_re_duration = re.compile('_(\d*).mp3')
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
  """ Download a file from the cloud and put it in a servicable place. """
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
      logging.debug('Unable to retreive %s from the cloud. It is not there' % path)

      # TODO: This is a pretty deep (and probably wrong) place to do this.
      DB.unregister_stream(path)

    except Exception as e:
      logging.debug('Unable to retreive %s from the cloud.' % path)

  return False

