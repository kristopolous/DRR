#!/usr/bin/python -O
import binascii

with open('../misc/test.mp3', 'rb') as f:
  while True:
    chunk = f.read(1)
    if chunk:
      print chunk[0] == '\xff'
      print "%s" % binascii.b2a_hex(chunk)
    else:
      break

