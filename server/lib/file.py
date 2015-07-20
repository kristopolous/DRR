#!/usr/bin/python -O
import os
import logging

g_config = {}

def set_config(config):
  global g_config
  g_config = config

def get(path):
  """
  If the file exists locally then we return it, otherwise
  we go out to the network store and retrieve it
  """
  if os.path.exists(path):
    return open(path, 'rb')

  else:
    res = download(path)
    if res:
      return open(path, 'rb')

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

