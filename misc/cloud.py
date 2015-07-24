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

  print " Station   Files   Space (GB)"
  print "-----------------------------"
  for station in sorted(station_list):
    sys.stdout.write( "%2d: %s " % (len(station_list) - ix + 1, station) )
    sys.stdout.flush()
    by_station[station] = [ f for f in blob_service.list_blobs('streams', prefix=station) ]
    total_space = sum([ f.properties.content_length for f in by_station[station] ])
    sys.stdout.write( " %5d %9.3f\n" % (len(by_station[station]),  total_space / (1024.0 ** 3)) )
    all_files += by_station[station]
    ix += 1

  all_props = [ f.properties for f in all_files ]
  disk_space = [ f.content_length for f in all_props ]

  gb = sum(disk_space) / (1024.0 ** 3)
  print "-----------------------------"
  print " %-8s %5d %9.3f GB" % ("Total", len(all_files), gb)
  print " %-7s  $%.02f/month" % ("Cost", gb * 0.024)
  print
  print " *using $0.024/GB azure pricing"


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

elif args.query == 'unlink':
  print "Reading files to unlink from stdin"

  for line in sys.stdin:
    print "Removing %s" % line
    cloud.unlink(line)
