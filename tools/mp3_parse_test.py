#!/usr/bin/python3 
#
# This is where the mp3 routines get testbedded before being integrated into the server
#
import binascii
import pdb
import os
import sys
import struct
import math
import base64
import marshal
from glob import glob

MAX_HEADER_ATTEMPTS = 102400






def mp3_info(b1, b2, b3):
  failCase = [ False, False, False, False, False ]

  mpegTable = [ 2, 1 ]
  layerTable = [ None, 3, 2, 1 ]
  
  freqTable = [  
    None,
    [ 44100, 48000, 32000, 0 ],
    [ 22050, 24000, 16000, 0 ]
  ]

  modeTable = [ 'stereo' , 'joint' , 'dual' , 'mono' ]
  brTable = [
    None, # MPEG-0 (doesn't exist)

    [ #MPEG-1 

      None, # layer 0 (Doesn't exist)

      [ # layer I 
        0,   32,  64,  96,  
        128, 160, 192, 224, 
        256, 288, 320, 352,
        384, 416, 448, 0 ],

      [ # layer II 
        0,   32,  48,  56, 
        64,  80,  96,  112, 
        128, 160, 192, 224, 
        256, 320, 384, 0 ],

      [ # layer III 
        0,   32,  40,  48, 
        56,  64,  80,  96, 
        112, 128, 160, 192, 
        224, 256, 320, 0 ]
    ],

    [ # MPEG-2

      None, # layer 0 (Doesn't exist)

      [ # layer 1
        0,   32,  64,  96, 
        128, 160, 192, 224, 
        256, 288, 320, 352,
        384, 416, 448, 0 ],

      [ # layer II 
        0,   32,  48,  56, 
        64,  80,  96,  112, 
        128, 160, 192, 224, 
        256, 320, 384, 0 ],

      [ # layer III 
        0,   8,   16,  24,
        32,  64,  80,  56,
        64,  128, 160, 112, 
        128, 256, 320, 0 ]
    ]
  ]

  b = b1 & 0xf
  mpeg = mpegTable[b >> 3]
  layer = layerTable[(b >> 1) & 0x3]
  protection_bit = b & 1
  
  if mpeg is None or layer != 3: return failCase

  samp_rate = freqTable[mpeg][(b2 & 0x0f) >> 2]
  bit_rate = brTable[mpeg][layer][b2 >> 4]
  pad_bit = (b2 & 0x3) >> 1
  mode = modeTable[(b3 >> 6)]

  if not bit_rate or not samp_rate: return failCase

  # from http://id3.org/mp3Frame
  # It's a wiki I can't register on for some reason. It's slightly incorrect
  if mode == 'joint':
    multiplier = 144000
    #multiplier = 72000
  else:
    multiplier = 144000
  frame_size = int((multiplier * bit_rate / samp_rate) + pad_bit)

  return frame_size, samp_rate, bit_rate, pad_bit, mode

def mp3_sig(file_name, blockcount = -1):
  #pdb.set_trace()
  frame_sig = []
  start_byte = []
  chain = []
  rsize = 8

  frame_size = None
  assumed_set = None
  attempt_set = None
  next_read = False

  file_handle = open(file_name, 'rb')

  first_header_seen = False
  header_attempts = 0

  while blockcount != 0:

    if first_header_seen:
      blockcount -= 1

    else:
      header_attempts += 1 

    if next_read:
      file_handle.seek(next_read, 0)
      next_read = False

    frame_start = last_read = file_handle.tell()

    header = file_handle.read(2)
    #print(binascii.b2a_hex(header))
    if header:

      b1 = header[1]

      if header[0] == 0xff and (b1 >> 4) == 0xf:

        try:
          b2 = ord(file_handle.read(1))
          b3 = ord(file_handle.read(1))
          # If we are at the EOF
        except:
          break

        if frame_size and not assumed_set:
          attempt_set = [samp_rate, bit_rate, pad_bit]

        frame_size, samp_rate, bit_rate, pad_bit, mode = mp3_info(b1, b2, b3)
        print(hex(file_handle.tell()), hex(frame_size), samp_rate, bit_rate, pad_bit, mode)


        if not frame_size:
          next_read = last_read + 1
          continue

        # We make sure that we get the same set of samp_rate, bit_rate, pad_bit twice
        if not assumed_set and attempt_set == [samp_rate, bit_rate, pad_bit]:
          assumed_set = attempt_set
          attempt_set = False

        # This is another indicator that we could be screwing up ... 
        elif assumed_set and samp_rate != assumed_set[0] and bit_rate != assumed_set[1]:
          print("rates are off assumed set, going back")
          next_read = last_read + 1
          continue


        if not first_header_seen:
          print(hex(file_handle.tell()), "First header", frame_size, samp_rate, bit_rate, assumed_set)
          first_header_seen = True


        # Get the signature
        sig = file_handle.read(rsize)
        frame_sig.append(sig)
        start_byte.append(frame_start)
        #print('start %x' % frame_start)

        # Move forward the frame file_handle.read size + 4 byte header
        throw_away = file_handle.read(frame_size - (rsize + 4))


      # ID3 tag for some reason
      elif header == b'\x49\x44':
        # Rest of the header
        throw_away = file_handle.read(4)

        # Quoting http://id3.org/d3v2.3.0
        #
        # The ID3v2 tag size is encoded with four bytes where the most
        # significant bit (bit 7) is set to zero in every byte, making a total
        # of 28 bits. The zeroed bits are ignored, so a 257 bytes long tag is
        # represented as $00 00 02 01.
        #
        candidate = struct.unpack('>I', file_handle.read(4))[0]
        size = ((candidate & 0x007f0000) >> 2 ) | ((candidate & 0x00007f00) >> 1 ) | (candidate & 0x0000007f)
        print("ID3 Tag length {} ".format(size))
        
        file_handle.read(size)

      # ID3 TAG -- 128 bytes long
      elif header == b'\x54\x41':
        # We've already read 2 so we can go 126 forward
        file_handle.read(126)

      elif header_attempts > MAX_HEADER_ATTEMPTS:

        print("%d[%d/%d]%s:%s:%s %s %d" % (len(frame_sig), header_attempts, MAX_HEADER_ATTEMPTS, binascii.b2a_hex(header), binascii.b2a_hex(file_handle.read(5)), file_name, hex(file_handle.tell()), len(start_byte) * (1152.0 / 44100) / 60))

        # This means that perhaps we didn't guess the start correct so we try this again
        if len(frame_sig) == 1 and header_attempts < MAX_HEADER_ATTEMPTS:
          print("False start -- trying again")

          # seek to the first start byte + 1
          file_handle.seek(start_byte[0] + 2)

          # discard what we thought was the first start byte and
          # frame signature
          start_byte = []
          frame_sig = []
          first_header_seen = False

        else:
          break

      elif first_header_seen:
        next_read = last_read + 1
        header_attempts += 1 
        print(hex(file_handle.tell()), "Looking for header", binascii.b2a_hex(header), "%x %d" % (file_handle.tell(), len(frame_sig)))
        if len(frame_sig) == 1:

          # discard what we thought was the first start byte and
          # frame signature
          start_byte = []
          frame_sig = []
          first_header_seen = False

          # Also our assumed set was probably wrong
          assumed_set = None

          
      else:
        next_read = last_read + 1

    else:
      break

  file_handle.close()
  return [frame_sig, start_byte]

# serialize takes a list of ordinal tuples and makes
# one larger mp3 out of it. The tuple format is
# (fila_name, byte_start, byte_end) where byte_end == -1 
# means "the whole file" 
def audio_serialize(file_list, out_path='/tmp/serialize.mp3'):
  print(">>", out_path)
  out = open(out_path, 'wb+')

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


def audio_type(file_name):
  """ 
  Determines the audio type of an file_name and returns where the start of
  the audio block is.
  """
  f = open(file_name, 'rb')

  # mp3 blocks appear to be \xff\xfb | \x49\x44 | \x54\x41
  # aac is \xff(\xf6 == \xf0) ... 
  while True:
    pos = f.tell()

    try:
      b0 = ord(f.read(1))

    except:
      break

    if b0 == 0xff:
      b1 = ord(f.read(1))

      if b1 & 0xf6 == 0xf0:
        return 'aac', pos

      elif b1 == 0xfb or b1 == 0xfa:
        # In order to see if it's an mp3 or not we read the next byte
        # and try to get the stats on the frame
        b = ord(f.read(1))
        frame_size, samp_rate, bit_rate, pad_bit = mp3_info(b, b1)

        # If there's a computed frame_size then we can continue
        if frame_size:
          # We try to move forward and see if our predictive 
          # next block works. 
          f.seek(pos + frame_size)

          # If this is an mp3 file and that frame was valid, then
          # we should now be at the start of the next frame.
          b0, b1 = [ord(byte) for byte in f.read(2)]

          if b0 == 0xff and b1 == 0xfb or b1 == 0xfa:
            # That's good enough for us
            return 'mp3', pos

      f.seek(pos + 1)

  return None, None

def audio_slice(file_name, start, end):
  # Most common frame-length ... in practice, I haven't 
  # seen other values in the real world
  frame_length = (1152.0 / 44100)
  crc32, offset = mp3_sig(file_name)

  frame_start = int(math.floor(start / frame_length))
  frame_end = int(math.ceil(end / frame_length))

  out = open('/tmp/attempt.mp3', 'wb+')
  f = open(file_name, 'rb')

  f.seek(offset[frame_start])
  out.write(f.read(offset[frame_end] - offset[frame_start]))
  f.close()
  out.close()

  return True

def audio_stitch(file_list, cb_sig=mp3_sig):
  print(file_list)
  first = {'name': file_list[0]}

  crc32, offset = cb_sig(first['name'])

  first['crc32'] = crc32
  first['offset'] = offset

  # Use the first offset and not the 0 byte.
  args = [(first['name'], first['offset'][0], first['offset'][-1])]

  for name in file_list[1:]:
    second = {'name': name}

    crc32, offset = cb_sig(name)
    #print(crc32)

    second['crc32'] = crc32
    second['offset'] = offset

    print(len(first['crc32']), offset[0], first['offset'][0], len(second['crc32']))

    isFound = False
    passed = False
    firstOffset = 0

    print(binascii.b2a_hex(first['crc32'][-40]), "%x" % first['offset'][-40])
    
    """ 
    for x in range(len(second['crc32'])):
        print(binascii.b2a_hex(second['crc32'][x]), "%x" % (second['offset'][x]))
    """ 
    print(second['crc32'][:10])
    print(first['crc32'][-10:])
    for j in range(-27, -2): 
      if first['crc32'][j] not in second['crc32']:
        print("No for {}".format(j))
        continue

      print("Yes for {}".format(j))
      pos = second['crc32'].index(first['crc32'][j])

      passed = True
      for i in range(5, 1, -1):
        if second['crc32'][pos - i + -j] != first['crc32'][-i]:
          passed = False
          print("Indices do not match between %s and %s" % (first['name'], second['name']))
          break

      if passed:
        isFound = True
        firstOffset = j
        break
      break

    if not isFound:
      raise Exception("Cannot find indices between %s and %s" % (first['name'], second['name']))
      break

    if isFound:
      args.append((second['name'], second['offset'][pos], second['offset'][firstOffset]))
      first = second
      continue

    break


  # Since we end at the last block, we can safely pass in a file1_stop of 0
  if len(args) > 1:
    # And then we take the offset in the crc32_second where things began, + 1
    audio_serialize(args)
    return True

def audio_tag(source, length_sec, out):
  length_ms = length_sec * 1000
  # Make sure our size to inject is 8 bytes long
  tlen_payload = ("%s%s" % ('\x00' * 8, str(length_ms)))[-9:]
  print(tlen_payload)
  tlen = 'TLEN\x00\x00\x00\x08\x40%s' % (tlen_payload)
  print(len(tlen))

  # Our ID3 length is a constant since we are just doing this to make itunes happy.
  block = 'ID3\x03\x00\x00\x00\x00\x00\x12%s' % tlen
  with open(out, 'wb') as out:
    out.write(block)
    with open(source, 'rb') as infile:
      out.write(infile.read())

if __name__ == "__main__":
  print(audio_stitch(sys.argv[1:]))
  """
  for file_name in sys.argv[1:]:
    sig, block = mp3_sig(file_name)
    print(len(block))

  sys.exit(0)

  audio_tag('/home/chris/radio/kpcc/streams/kpcc-1437707563.mp3', 2 * 60 * 60, '/tmp/audio')


  for f in fail_list.split(' '):
    fsize = os.path.getsize(f)
    #try:
    if fsize > 50000:
      p = mp3_sig(f)
      if p:
        print(len(p[0]) / fsize, len(p[0]), fsize, f)
      else:
        print("FAILURE: %s" % f)

  sys.exit(0)

  #sys.exit(0)
  #isSuccess = audio_stitch(["/var/radio/kpcc-1435670337.mp3","/var/radio/kpcc-1435671243.mp3"])

  # failure case
  #stitch_attempt('/var/radio/kpcc-1435670339.mp3', '/var/radio/kpcc-1435669435.mp3')

  # audio_slice('/tmp/serialize.mp3', 14 * 60, 16 * 60)
  """
