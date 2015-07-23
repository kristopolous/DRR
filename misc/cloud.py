#!/usr/bin/python -O
import argparse
import os
import re
import sys
from glob import glob
import ConfigParser
from azure.storage import BlobService
import lib.cloud as cloud
import lib.misc as misc

def get_files(station_list, blob_service):
  for station in station_list:
    for f in blob_service.list_blobs('streams', prefix=station):
      print f.name

def get_size(station_list, blob_service):
  all_files = []
  by_station = {}
  ix = 1

  for station in station_list:
    sys.stdout.write( "[ %d / %d ] %s " % (ix, len(station_list), station) )
    sys.stdout.flush()
    by_station[station] = [ f for f in blob_service.list_blobs('streams', prefix=station) ]
    sys.stdout.write( "... %d\n" % len(by_station[station]) )
    all_files += by_station[station]
    ix += 1

  all_props = [ f.properties for f in all_files ]
  disk_space = [ f.content_length for f in all_props ]

  print "total:", sum(disk_space) / (1024.0 ** 3)
  print "files:", len(all_files)

  # by station
  for station, prop in by_station.items():
    total_space = sum([ f.properties.content_length for f in prop ])
    print station, len(prop), total_space / (1024.0 ** 3) 

cfg = os.environ.get('CLOUD_CFG')

os.chdir(os.path.dirname(os.path.realpath(__file__)))

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--station", default="all", help="station to query (default all)")
parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
parser.add_argument("-q", "--query", default="size", help="query to send to the cloud (list, size, unlink)")
args = parser.parse_args()

if args.config is None:
  print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
  sys.exit(-1)

if args.station == 'all':
  args.station = re.sub('.txt', '', ','.join([ os.path.basename(path) for path in glob('../server/configs/*txt')]))

station_list = args.station.split(',')

cloud_config = ConfigParser.ConfigParser()
cloud_config.read(args.config)
config = {'azure': misc.config_section_map('Azure', cloud_config)}

blob_service, container = cloud.connect(config)

if args.query == 'size':
  get_size(station_list, blob_service)

elif args.query == 'list':
  get_files(station_list, blob_service)
