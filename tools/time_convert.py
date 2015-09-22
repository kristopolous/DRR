#!/usr/bin/python -O
import sys
import lib.misc as misc
import lib.ts as TS

all_data = sys.stdin.readlines()[0]
for data in all_data.split('_'):
  parts = data.split(' ')
  print "%f %f" % ( TS.to_utc(parts[0], parts[1]),  TS.duration_parse(parts[2]) )
