#!/usr/bin/python -O
import sys
import lib.misc as misc
import lib.ts as TS

all_data = sys.stdin.readlines()[0]
for data in all_data.split('_'):
  parts = data.split(' ')
  print TS.to_utc(parts[0], parts[1])
