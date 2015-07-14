#!/usr/bin/python -O
import binascii
import sys
import struct
import math
import base64
from glob import glob

MAX_HEADER_ATTEMPTS = 1024
def hash_test(file_list):
  for name in file_list:
    audio_crc(name)

def audio_crc(fname, blockcount = -1):
  frame_sig = []
  start_byte = []
  rsize = 64

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
        first_header_seen = True
        b = ord(f.read(1))

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        frame_size = (144000 * bit_rate / samp_rate) + pad_bit

        # Rest of the header
        throw_away = f.read(1)
        #print samp_rate, bit_rate, hex(ord(throw_away))

        # Get the signature
        #print "%s %d" % (hex(frame_start), rsize)
        block = f.read(rsize)
        #print "%s" % (binascii.b2a_hex(block))
        crc = binascii.crc32(block)

        frame_sig.append(crc)

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

#for f in glob.glob("*.mp3"):
#    p =  mp3_crc(f)
    #print len(p[0])

# success case
audio_crc(sys.argv[1])

sys.exit(0)
#isSuccess = audio_stitch(["/var/radio/kpcc-1435670337.mp3","/var/radio/kpcc-1435671243.mp3","/var/radio/kpcc-1435672147.mp3","/var/radio/kpcc-1435673051.mp3","/var/radio/kpcc-1435673955.mp3","/var/radio/kpcc-1435674859.mp3","/var/radio/kpcc-1435675763.mp3","/var/radio/kpcc-1435676667.mp3","/var/radio/kpcc-1435677571.mp3","/var/radio/kpcc-1435678475.mp3","/var/radio/kpcc-1435679379.mp3"])

# failure case
#stitch_attempt('/var/radio/kpcc-1435670339.mp3', '/var/radio/kpcc-1435669435.mp3')

audio_slice('/tmp/serialize.mp3', 14 * 60, 16 * 60)
