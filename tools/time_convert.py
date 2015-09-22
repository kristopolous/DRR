#!/usr/bin/python -O
import json
import lib.ts as TS

all_data = raw_input()

res = []
for data in all_data.split('_'):
  parts = data.strip().split(' ')
  res.append((TS.to_utc(parts[0], parts[1]), TS.duration_parse(parts[2])))

print json.dumps(res)
