#!/usr/bin/python -O
import sys
import json
import lib.ts as TS

all_data = sys.stdin.readlines()[0]

res = []
for data in all_data.split('_'):
  parts = data.strip().split(' ')
  res.append((TS.to_utc(parts[0], parts[1]),  TS.duration_parse(parts[2]) ))

print json.dumps(res)
