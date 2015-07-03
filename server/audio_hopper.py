#!/usr/bin/python -O
import binascii

with open('../misc/test.mp3', 'rb') as f:

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  while True:
    header = f.read(2)
    if header:
      # print "candidate: %s" % binascii.b2a_hex(header)

      if header == '\xff\xfb':
        b_dat = f.read(1)
        b = ord(b_dat)
        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        frame_size = (144000 * bit_rate / samp_rate) + pad_bit
        f.seek(frame_size + f.tell() - 3)

        #print "framesize, pos: %d %d %d %s %d %d" % (frame_size, f.tell(), pad_bit, binascii.b2a_hex(b_dat), bit_rate, samp_rate)
        #print "%s" % binascii.b2a_hex(chunk)
      else:
        print "WRONG"
    else:
      break

