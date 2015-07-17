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

all_files = []
by_station = {}
# total storage 
for station in ['wfmu']:#'kxlu kpcc kdvs wxyc wcbn wfmu kzsu kvrx'.split(' '):
   print "Retrieving %s" % station
   by_station[station] = [ f for f in blob_service.list_blobs('streams', prefix=station, maxresults = 500) ]
   all_files += by_station[station]

for fname in by_station['wfmu']:
    print "Deleting ", fname.name
    blob_service.delete_blob(container, fname.name)
sys.exit(0)

all_props = [ f.properties for f in all_files ]
disk_space = [ f.content_length for f in all_props ]

print "total:", sum(disk_space) / (1024.0 ** 3)
print "files:", len(all_files)


# by station
for station, prop in by_station.items():
  total_space = sum([ f.properties.content_length for f in prop ])
  print station, len(prop), total_space / (1024.0 ** 3) 
