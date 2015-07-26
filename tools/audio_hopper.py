#!/usr/bin/python -O
#
# This is where the mp3 routines get testbedded before being integrated into the server
#
import binascii
import os
import sys
import struct
import math
import base64
import marshal
from glob import glob

MAX_HEADER_ATTEMPTS = 1024
def hash_test(file_list):
  for name in file_list:
    audio_crc(name)

def make_map(fname):
  obj = audio_crc(fname)
  print len(obj[0])
  marshal.dump(obj, open(fname + '.map', 'wb'))

def audio_crc(fname, blockcount = -1):
  frame_sig = []
  start_byte = []
  chain = []
  rsize = 4

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  f = open(fname, 'rb')

  first_header_seen = False
  header_attempts = 0

  while blockcount != 0:

    if first_header_seen:
      blockcount -= 1

    else:
      header_attempts += 1 
      if header_attempts > 2:
        # Go 1 back.
        f.seek(-1, 1)


    frame_start = f.tell()
    header = f.read(2)
    if header:

      if header == '\xff\xfb' or header == '\xff\xfa':
        try:
          b = ord(f.read(1))
          # If we are at the EOF
        except:
          break

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        try:
          frame_size = (144000 * bit_rate / samp_rate) + pad_bit

        except:
          continue

        if not first_header_seen:
          first_header_seen = True

        # Rest of the header
        throw_away = f.read(1)
        #print samp_rate, bit_rate, hex(ord(throw_away))

        # Get the signature
        #print "%s %d" % (hex(frame_start), rsize)
        #if len(chain) > 4:
        #  print "%s" % (' '.join([binascii.b2a_hex(block) for block in chain]))
        #  chain.pop(0)
          
        sig = f.read(rsize)
        frame_sig.append(sig)
        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - (rsize + 4))

      #ID3 tag for some reason
      elif header == '\x49\x44':
        # Rest of the header
        throw_away = f.read(4)

        # Quoting http://id3.org/d3v2.3.0
        #
        # The ID3v2 tag size is encoded with four bytes where the most
        # significant bit (bit 7) is set to zero in every byte, making a total
        # of 28 bits. The zeroed bits are ignored, so a 257 bytes long tag is
        # represented as $00 00 02 01.
        #
        candidate = struct.unpack('>I', f.read(4))[0]
        size = ((candidate & 0x007f0000) >> 2 ) | ((candidate & 0x00007f00) >> 1 ) | (candidate & 0x0000007f)
        
        f.read(size)

      # ID3 TAG -- 128 bytes long
      elif header == '\x54\x41':
        # We've already read 2 so we can go 126 forward
        f.read(126)

      elif first_header_seen or header_attempts > MAX_HEADER_ATTEMPTS:

        print "%d[%d/%d]%s:%s:%s %s %d" % (len(frame_sig), header_attempts, MAX_HEADER_ATTEMPTS, binascii.b2a_hex(header), binascii.b2a_hex(f.read(5)), fname, hex(f.tell()), len(start_byte) * (1152.0 / 44100) / 60)

        # This means that perhaps we didn't guess the start correct so we try this again
        if len(frame_sig) == 1 and header_attempts < MAX_HEADER_ATTEMPTS:
          print "False start -- trying again"

          # seek to the first start byte + 1
          f.seek(start_byte[0] + 2)

          # discard what we thought was the first start byte and
          # frame signature
          start_byte = []
          frame_sig = []
          first_header_seen = False

        else:
          break

    else:
      break

  f.close()
  return [frame_sig, start_byte]

# serialize takes a list of ordinal tuples and makes
# one larger mp3 out of it. The tuple format is
# (fila_name, byte_start, byte_end) where byte_end == -1 
# means "the whole file" 
def audio_serialize(file_list):
  out = open('/tmp/serialize.mp3', 'wb+')

  for name, start, end in file_list:
    f = open(name, 'rb')

    f.seek(start)
    
    if end == -1:
      out.write(f.read())
    else:
      out.write(f.read(end - start))

    f.close()

  out.close()

  return True

def audio_slice(fname, start, end):
  # Most common frame-length ... in practice, I haven't 
  # seen other values in the real world
  frame_length = (1152.0 / 44100)
  crc32, offset = audio_crc(fname)

  frame_start = int(math.floor(start / frame_length))
  frame_end = int(math.ceil(end / frame_length))

  out = open('/tmp/attempt.mp3', 'wb+')
  f = open(fname, 'rb')

  f.seek(offset[frame_start])
  out.write(f.read(offset[frame_end] - offset[frame_start]))
  f.close()
  out.close()

  return True

def audio_stitch(file_list):
  first = {'name': file_list[0]}

  crc32, offset = audio_crc(first['name'])

  first['crc32'] = crc32
  first['offset'] = offset

  args = [(first['name'], 0, first['offset'][-1])]

  for name in file_list[1:]:
    second = {'name': name}

    crc32, offset = audio_crc(name)

    second['crc32'] = crc32
    second['offset'] = offset

    isFound = True

    try:
      pos = second['crc32'].index(first['crc32'][-2])

      for i in xrange(5, 1, -1):
        if second['crc32'][pos - i + 2] != first['crc32'][-i]:
          isFound = False
          print "Indices do not match between %s and %s" % (first['name'], second['name'])
          break

    except: 
      raise "Cannot find indices between %s and %s" % (first['name'], second['name'])
      break

    if isFound:
      args.append((second['name'], second['offset'][pos], second['offset'][-2]))
      first = second
      continue

    break


  # Since we end at the last block, we can safely pass in a file1_stop of 0
  if len(args) > 1:
    # And then we take the offset in the crc32_second where things began, + 1
    audio_serialize(args)
    return True

def audiotag(source, length_sec, out):
  length_ms = length_sec * 1000
  # Make sure our size to inject is 8 bytes long
  tlen_payload = ("%s%s" % ('\x00' * 8, str(length_ms)))[-9:]
  print tlen_payload
  tlen = 'TLEN\x00\x00\x00\x08\x40%s' % (tlen_payload)
  print len(tlen)

  # Our ID3 length is a constant since we are just doing this to make itunes happy.
  block = 'ID3\x03\x00\x00\x00\x00\x00\x12%s' % tlen
  with open(out, 'wb') as out:
    out.write(block)
    with open(source, 'rb') as infile:
      out.write(infile.read())

audiotag('/home/chris/radio/kpcc/streams/kpcc-1437707563.mp3', 2 * 60 * 60, '/tmp/audio')

sys.exit(0)
#fail_list = '/raid/analyze/wxyc-1436334009.mp3 /raid/analyze/wxyc-1436448501.mp3 /raid/analyze/wxyc-1436555370.mp3 /raid/analyze/wxyc-1436408965.mp3 /raid/analyze/wxyc-1436322244.mp3 /raid/analyze/wxyc-1436318625.mp3 /raid/analyze/wxyc-1436407155.mp3 /raid/analyze/wxyc-1437035272.mp3 /raid/analyze/wxyc-1436587070.mp3 /raid/analyze/wxyc-1436903564.mp3 /raid/analyze/wxyc-1437047317.mp3 /raid/analyze/wxyc-1436688334.mp3 /raid/analyze/wxyc-1436835377.mp3 /raid/analyze/wxyc-1436380054.mp3 /raid/analyze/wxyc-1437013904.mp3 /raid/analyze/wxyc-1436667752.mp3 /raid/analyze/wxyc-1436470209.mp3 /raid/analyze/wxyc-1436776080.mp3 /raid/analyze/wxyc-1436338534.mp3 /raid/analyze/wxyc-1436959726.mp3 /raid/analyze/wxyc-1436971489.mp3 /raid/analyze/wxyc-1436376449.mp3 /raid/analyze/wxyc-1436627758.mp3 /raid/analyze/wxyc-1436957012.mp3'

#for f in glob("/raid/analyze/*.mp3"):
for f in fail_list.split(' '):
  fsize = os.path.getsize(f)
  #try:
  if fsize > 50000:
    p = audio_crc(f)
    if p:
      print float(len(p[0])) / fsize, len(p[0]), fsize, f
    else:
      print "FAILURE: %s" % f

sys.exit(0)
# success case
#make_map(sys.argv[1])
#audio_crc(sys.argv[1])

#sys.exit(0)
isSuccess = audio_stitch(["/var/radio/kpcc-1435670337.mp3","/var/radio/kpcc-1435671243.mp3"])

# failure case
#stitch_attempt('/var/radio/kpcc-1435670339.mp3', '/var/radio/kpcc-1435669435.mp3')

audio_slice('/tmp/serialize.mp3', 14 * 60, 16 * 60)
