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
        #print crc
        frame_sig.append(crc)
        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - 36)

      else:
        print "WRONG"

    else:
      break

  f.close()
  return [frame_sig, start_byte]

def serialize(file1, file1_stop, file2, file2_start):
  out = open('/tmp/attempt.mp3', 'rb+')
  f = open(file1, 'rb')

  if file1_stop == 0:
    out.write(f.read())
  else:
    out.write(f.read(file1_stop))

  f.close()

  f = open(file2, 'rb')
  f.seek(file2_start)
  out.write(f.read())

  f.close()
  out.close()
  return True

def stitch_attempt(first, second):
  crc32_first, offset_first = mp3_crc(first)
  crc32_second, offset_second = mp3_crc(second, 2000)

  last = 0
  isFound = True

  for i in xrange(4, 0, -1):
    pos = crc32_second.index(crc32_first[-i])
    if last != 0 and pos - last != 1:
      isFound = False

    last = pos

  # Since we end at the last block, we can safely pass in a file1_stop of 0
  if isFound:
    # And then we take the offset in the crc32_second where things began, + 1
    serialize(first, offset_first[-1], second, offset_second[last])

  print isFound

print mp3_crc('/var/radio/kpcc-1435670339.mp3')
print mp3_crc('/tmp/attempt.mp3')
#stitch_attempt('/var/radio/kpcc-1435669435.mp3', '/var/radio/kpcc-1435670339.mp3')
