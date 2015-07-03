#!/usr/bin/python -O
import binascii

def mp3_crc(fname, blockcount = -1):
  frame_sig = []
  start_byte = []

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]


  f = open(fname, 'rb')
  while blockcount != 0:
    blockcount -= 1

    header = f.read(2)
    if header:

      if header == '\xff\xfb' or header == '\xff\xfa':
        b = ord(f.read(1))
        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1
        frame_start = f.tell() - 3
        # from http://id3.org/mp3Frame
        frame_size = (144000 * bit_rate / samp_rate) + pad_bit

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        frame_sig.append(binascii.crc32(f.read(32)))
        start_byte.append(frame_start)

        # Move forward the frame
        throw_away = f.read(frame_size - 36)

      else:
        print "WRONG"

    else:
      break

  f.close()
  return [frame_sig, start_byte]

def stitch_attempt(first, second):
  crc32_first = mp3_crc(first)
  crc32_second = mp3_crc(second, 50)

  print crc32_first, crc32_second

stitch_attempt('/var/radio/kpcc-1435799122.mp3', '/var/radio/kpcc-1435800025.mp3')
