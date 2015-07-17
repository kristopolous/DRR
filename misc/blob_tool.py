#!/usr/bin/python -O
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

cfg = os.environ.get('CLOUD_CFG')
if cfg is None:
  print "Define the cloud configuration location with the CLOUD_CFG environment variable"
  sys.exit(-1)

cloud_config = ConfigParser.ConfigParser()
cloud_config.read(cfg)
config = config_section_map('Azure', cloud_config)

container = 'streams'
blob_service = BlobService(config['storage_account_name'], config['primary_access_key'])

# total storage 
all_files = [ f for f in blob_service.list_blobs('streams') ]
all_props = [ f.properties for f in all_files ]
disk_space = [ f.content_length for f in all_props ]

print "total:", sum(disk_space) / (1024.0 ** 3)

# by station
bucketMap = {}
for f in all_files:
  name = f.name
  station = re.findall('^(\w*)-', name)[0]
  if station not in bucketMap:
    bucketMap[station] = {'space': 0, 'count': 0}

  bucketMap[station]['count'] += 1
  bucketMap[station]['space'] += f.properties.content_length

for station, stats in bucketMap.items():
  print station, stats['count'], stats['space'] / ( 1024.0 ** 3)
