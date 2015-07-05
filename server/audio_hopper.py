#!/usr/bin/python -O
import binascii
import struct
import math
import base64

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

    frame_start = f.tell()
    header = f.read(2)
    if header:

      if header == '\xff\xfb' or header == '\xff\xfa':
        b = ord(f.read(1))

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        frame_size = (144000 * bit_rate / samp_rate) + pad_bit

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        crc = binascii.crc32(f.read(32))

        frame_sig.append(crc)

        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - 36)

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

      else:
        print "%s:%s:%s:%s %s" % (binascii.b2a_hex(header), header, f.read(5), fname, hex(f.tell()))
        break

    else:
      break

  f.close()
  return [frame_sig, start_byte]

# serialize takes a list of ordinal tuples and makes
# one larger mp3 out of it. The tuple format is
# (fila_name, byte_start, byte_end) where byte_end == -1 
# means "the whole file" 
def serialize(file_list):
  out = open('/tmp/serialize.mp3', 'wb+')

  for name, start, end in file_list:
    f = open(name, 'rb')

    f.seek(start)
    
    if end == -1:
      out.write(f.read())
    else:
      out.write(f.read(end))

    f.close()

  out.close()

  return True

def slice_audio(fname, start, end):
  # Most common frame-length ... in practice, I haven't 
  # seen other values in the real world
  frame_length = (1152.0 / 44100)
  crc32, offset = mp3_crc(fname)

  frame_start = int(math.floor(start / frame_length))
  frame_end = int(math.ceil(end / frame_length))

  out = open('/tmp/attempt.mp3', 'wb+')
  f = open(fname, 'rb')

  f.seek(offset[frame_start])
  out.write(f.read(offset[frame_end] - offset[frame_start]))
  f.close()
  out.close()

  return True

def stitch_attempt(file_list):
  first = {'name': file_list[0]}

  crc32, offset = mp3_crc(first['name'])

  first['crc32'] = crc32
  first['offset'] = offset

  args = [(first['name'], 0, first['offset'][-1])]

  for name in file_list[1:]:
    second = {'name': name}

    # if we are at the end, we only need a few
    if name == file_list[-1]:
      crc32, offset = mp3_crc(name, 2000)
    else:
      crc32, offset = mp3_crc(name)

    second['crc32'] = crc32
    second['offset'] = offset

    isFound = True

    try:
      pos = second['crc32'].index(first['crc32'][-1])

      for i in xrange(4, 0, -1):
        if second['crc32'][pos - i + 1] != first['crc32'][-i]:
          isFound = False
          break

    except: 
      break

    if isFound:
      args.append((second['name'], second['offset'][pos], second['offset'][-1]))
      first = second
      next

    break


  # Since we end at the last block, we can safely pass in a file1_stop of 0
  if len(args) > 1:
    # And then we take the offset in the crc32_second where things began, + 1
    serialize(args)
    return True
    #serialize([(first, 0, offset_first[-1]), (second, offset_second[pos], -1)])


#for f in glob.glob("*.mp3"):
#    p =  mp3_crc(f)
    #print len(p[0])

# success case
stitch_attempt(['/var/radio/kpcc-1435669435.mp3', '/var/radio/kpcc-1435670339.mp3'])

# failure case
#stitch_attempt('/var/radio/kpcc-1435670339.mp3', '/var/radio/kpcc-1435669435.mp3')

slice_audio('/tmp/serialize.mp3', 14 * 60, 16 * 60)
