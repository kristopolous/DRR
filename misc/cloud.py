#!/usr/bin/python -O
import argparse
import sqlite3
import os
import re
import sys
import ConfigParser
from azure.storage import BlobService
import lib.misc as misc


def cloud_connect(config):
  cloud_config = ConfigParser.ConfigParser()
  cloud_config.read(config)
  config = misc.config_section_map('Azure', cloud_config)

  container = 'streams'
  return container, BlobService(config['storage_account_name'], config['primary_access_key'])

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
conn = sqlite3.connect('../db/main.db')
db = {'conn': conn, 'c': conn.cursor()}

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--station", default="all", help="station to query (default all)")
parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
parser.add_argument("-q", "--query", default="size", help="query to send to the cloud")
args = parser.parse_args()

if args.config is None:
  print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
  sys.exit(-1)

if args.station == 'all':
  station_cur = db['c'].execute('select callsign from stations where active = 1')
  station_list = [ f[0] for f in station_cur.fetchall() ]

else:
  station_list = args.station.split(',')

container, blob_service = cloud_connect(args.config)

if args.query == 'size':
  get_size(station_list, blob_service)

elif args.query == 'list':
  get_files(station_list, blob_service)
