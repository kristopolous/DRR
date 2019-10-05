#!/usr/bin/python3 -O
import argparse
import os
import re
import sys
from glob import glob
import configparser
import textwrap
from azure.storage.blob import BlockBlobService as BlobService
import lib.cloud as cloud
import lib.misc as misc

def get_all(station):
  blobs = []
  marker = None
  while True:
    batch = blob_service.list_blobs('streams', prefix=station, marker=marker)
    blobs.extend(batch)
    if not batch.next_marker:
      break
    marker = batch.next_marker
  return blobs

def get_files(station_list, blob_service):
  from dateutil import parser
  for station in station_list:
    for f in get_all(station):
      dt = f.properties.last_modified #parser.parse(f.properties.last_modified)
      dt_str = dt.strftime('%Y%m%d%H%M%S')
      print('%s size: %10s date: %s' %(f.name, f.properties.content_length, dt_str))

def fail(why):
  import sys
  print("Failue: %s" % why)
  sys.exit(-1)

def get_size(station_list, blob_service):
  all_files = []
  by_station = {}
  ix = 1

  print(" Station   Files   Space (GB)")
  print("-----------------------------")
  for station in sorted(station_list):
    sys.stdout.write( "%2d: %s " % (len(station_list) - ix + 1, station) )
    sys.stdout.flush()
    by_station[station] = [ f for f in get_all(station) ]
    total_space = sum([ f.properties.content_length for f in by_station[station] ])
    sys.stdout.write( " %5d %9.3f\n" % (len(by_station[station]),  total_space / (1024.0 ** 3)) )
    all_files += by_station[station]
    ix += 1

  all_props = [ f.properties for f in all_files ]
  disk_space = [ f.content_length for f in all_props ]

  gb = sum(disk_space) / (1024.0 ** 3)
  print("-----------------------------")
  print(" %-8s %5d %9.3f GB" % ("Total", len(all_files), gb))
  print(" %-7s  $%.02f/month" % ("Cost", gb * 0.01))
  print()
  print(" *using $0.01/GB azure pricing")


cfg = os.environ.get('CLOUD_CFG')

os.chdir(os.path.dirname(os.path.realpath(__file__)))

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, epilog=textwrap.dedent('''\

    With no arguments, it tries to do some kind of accounting on how expensive a station is each month
    to keep it going.

    Examples:
      Removing files in batch:
      
      $ tools/cloud.py -q list -s KXXX | (whatever you want) | tools/cloud.py -q unlink
    '''))
parser.add_argument("-s", "--station", default="all", help="station to query (default all)")
parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
parser.add_argument("-q", "--query", default='size', help="query to send to the cloud (list, size, unlink)")
parser.add_argument("-g", "--get", help="get a file from the cloud")
parser.add_argument("-p", "--put", help="put a file into the cloud")
parser.add_argument("-d", "--rm", help="remove a file from the cloud")
args = parser.parse_args()

if args.config is None:
  print("Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option")
  sys.exit(-1)

if args.station == 'all':
  args.station = re.sub('.txt', '', ','.join([ os.path.basename(path) for path in glob('../server/configs/*txt')]))

station_list = args.station.split(',')

cloud_config = configparser.ConfigParser()
cloud_config.read(args.config)
config = {'azure': misc.config_section_map('Azure', cloud_config)}

blob_service, container = cloud.connect(config)

if args.get:
  print("Getting")
  for name in args.get.split(','):
    print(" ↓ %s" % name)
    res = cloud.download(name, name, config=config)
    if not res:
      sys.stderr.write("%s\n" % name)
      fail("Couldn't download %s" % name)

elif args.put:
  print("Putting")
  for name in args.put.split(','):
    print(" ↑ %s" % name)
    res = cloud.upload(name, name, config=config)
    if not res:
      sys.stderr.write("%s\n" % name)
      fail("Couldn't upload %s" % name)

elif args.rm:
  print("Removing")
  for name in args.rm.split(','):
    print(" - %s" % name)
    res = cloud.unlink(name, config=config)
    if not res:
      sys.stderr.write("%s\n" % name)
      fail("Couldn't delete %s" % name)

elif args.query == 'size':
  get_size(station_list, blob_service)

elif args.query == 'list':
  get_files(station_list, blob_service)

elif args.query == 'unlink':
  print("Reading files to unlink from stdin")

  for line in sys.stdin:
    full_line = line.strip()
    line = line.strip().split(' ')
    filename = line[0]
    print(" - %s" % full_line)
    cloud.unlink(filename, config=config)

elif args.query:
  print("Query '%s' not recognized. Possibilities are unlink, size, and list" % args.query)
