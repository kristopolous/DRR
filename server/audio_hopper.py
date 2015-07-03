#!/usr/bin/python -O
import binascii

with open('../misc/test.mp3', 'rb') as f:

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  while True:
    header = f.read(2)
    if header:
      if header == '\xff\xfb':
        b = ord(f.read(1))
        print (b & 0x0f) >> 2
        print freqTable[b >> 4]
        #print "%s" % binascii.b2a_hex(chunk)
    else:
      break

