#!/usr/bin/python -O
import argparse
import os
import re
import sys
import ConfigParser
from azure.storage import BlobService

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

def cloud_connect(config):
  cloud_config = ConfigParser.ConfigParser()
  cloud_config.read(config)
  config = config_section_map('Azure', cloud_config)

  container = 'streams'
  return container, BlobService(config['storage_account_name'], config['primary_access_key'])

def get_files(station_list, blob_service):
  for station in station_list:
    for f in blob_service.list_blobs('streams', prefix=station):
      print f.name

def get_size(station_list, blob_service):
  all_files = []
  by_station = {}

  for station in statoin_list:
    print "Retrieving %s" % station
    by_station[station] = [ f for f in blob_service.list_blobs('streams', prefix=station) ]
    all_files += by_station[station]

  all_props = [ f.properties for f in all_files ]
  disk_space = [ f.content_length for f in all_props ]

  print "total:", sum(disk_space) / (1024.0 ** 3)
  print "files:", len(all_files)

  # by station
  for station, prop in by_station.items():
    total_space = sum([ f.properties.content_length for f in prop ])
    print station, len(prop), total_space / (1024.0 ** 3) 

all_stations = 'kxlu kpcc kdvs wxyc wcbn wfmu kzsu kvrx'.split(' ')

cfg = os.environ.get('CLOUD_CFG')
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--station", default="all", help="station to query (default all)")
parser.add_argument("-c", "--config", default=cfg, help="cloud credential file ot use")
parser.add_argument("-q", "--query", default="size", help="query to send to the cloud")
args = parser.parse_args()

if args.config is None:
  print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
  sys.exit(-1)

container, blob_service = cloud_connect(args.config)

if args.station is not 'all':
  station_list = [args.station]

if args.query == 'size':
  get_size(station_list, blob_service)

elif args.query == 'list':
  get_files(station_list, blob_service)
