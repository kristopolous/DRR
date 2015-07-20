#!/usr/bin/python -O
import os
import re
import time 
import logging
import lib.misc as misc
import lib.db as DB
import lib.ts as TS
from glob import glob
from datetime import datetime, timedelta, date

g_config = {}

def set_config(config):
  global g_config
  g_config = config

def get(path, do_open=True):
  """
  If the file exists locally then we return it, otherwise
  we go out to the network store and retrieve it
  """
  if os.path.exists(path):
    if do_open: return open(path, 'rb')
    return True

  else:
    res = download(path)
    if res:
      if do_open: return open(path, 'rb')
      return True

  return False


def connect():
  """ Connect to the cloud service """
  from azure.storage import BlobService
  global g_config
  container = 'streams'

  blob_service = BlobService(g_config['azure']['storage_account_name'], g_config['azure']['primary_access_key'])
  blob_service.create_container(container, x_ms_blob_public_access='container')
  return blob_service, container


def unlink(path):
  """ Remove a file from the cloud service """
  fname = os.path.basename(path)
  blob_service, container = connect()
  return blob_service.delete_blob(container, path)


def put(path):
  blob_service, container = connect()

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


def prune():
  """ Gets rid of files older than archivedays - cloud stores things if relevant """

  global g_config
  pid = misc.change_proc_name("%s-cleanup" % g_config['callsign'])

  db = DB.connect()

  duration = g_config['archivedays'] * TS.ONE_DAY
  cutoff = time.time() - duration

  cloud_cutoff = False
  if g_config['cloud']:
    cloud_cutoff = time.time() - g_config['cloudarchive'] * TS.ONE_DAY

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

    elif cloud_cutoff and ctime < cloud_cutoff:
      logging.debug("Prune[cloud]: putting %s" % fname)
      put(fname)
      try:
        os.unlink(fname)
      except:
        logging.debug("Prune[cloud]: Couldn't remove %s" % fname)


  # The map names are different since there may or may not be a corresponding
  # cloud thingie associated with it.
  db = DB.connect()
  unlink_list = db['c'].execute('select name from streams where created_at < (current_timestamp - ?)', (duration, )).fetchall()

  for fname in unlink_list:
    # If there's a cloud account at all then we need to unlink the 
    # equivalent mp3 file
    if cloud_cutoff:
      unlink(fname[:-4])

    # now only after we've deleted from the cloud can we delete the local file
    os.unlink(fname)

  # After we remove these streams then we delete them from the db.
  db['c'].execute('delete from streams where name in ("%s")' % ('","'.join(unlink_list)))
  db['conn'].commit()

  logging.info("Found %d files older than %s days." % (count, g_config['archivedays']))
  misc.kill('prune') 


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
  blob_service, container = connect()

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

