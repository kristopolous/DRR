#!/usr/bin/python -O
import os
import math
import gzip
import marshal
import re
import struct
import logging
import misc
import cloud
import db as DB
import ts as TS
from datetime import datetime, timedelta, date

# Most common frame-length ... in practice, I haven't 
# seen other values in the real world.
FRAME_LENGTH = (1152.0 / 44100)

FORMAT_MP3 = 'mp3'
FORMAT_AAC = 'aac'

#
# Some stations don't start you off with a valid mp3 header
# (such as kdvs), so we have to just seek into the file
# and look for one.  This is the number of bytes we try.
# In practice, 217 appears to be enough, so we make it about
# ten times that and cross our fingers.
#
MAX_HEADER_ATTEMPTS = 2048

def list_info(file_list):
  """ A version of the stream_info that accepts a list. """
  info = stream_info(file_list[0]['name'])

  # Some things are the same such as the
  # week, start_minute, start_date
  info['duration_sec'] = 0
  for item in file_list:
    info['duration_sec'] += item['duration_sec']

  info['end_minute'] = (info['duration_sec'] / 60.0 + info['duration_sec']) % TS.MINUTES_PER_WEEK

  return info


def stream_info(fname, guess_time=False):
  """
  Determines the date the thing starts,
  the minute time it starts, and the duration

  If guess_time is set, then that value is used 
  as the audio time.  It can speed things up
  by avoiding an opening of the file all together.
  
  It's sometimes an ok thing to do.
  """
  if type(fname) is list:
    return list_info(fname)

  ts_re = re.compile('-(\d*)[.|_]')
  ts = ts_re.findall(fname)

  duration = 0
  start_minute = 0
  start_date = 0

  if ts:
    unix_time = int(ts[0])
    start_minute = TS.to_minute(unix_time)
    start_date = datetime.fromtimestamp(unix_time)

  else:
    logging.warn("Failure to find info for '%s'" % fname)
    return False

  duration = guess_time if guess_time else get_time(fname) 

  if not duration:
    # If we can't find a duration then we try to see if it's in the file name
    ts_re_duration = re.compile('_(\d*).{4}')
    ts = ts_re_duration.findall(fname)
    if ts:
      duration = int(ts[0]) * 60

  if not isinstance(duration, (int, long, float)):
    duration = 0

  # We represent non-existing files by saying they occupy -1 bytes.
  file_size = - 1
  if os.path.exists(fname):
    file_size = os.path.getsize(fname)

  return {
    # The week number 
    'week_number': start_date.isocalendar()[1], 
    'name': fname, 
    'start_minute': start_minute, 
    'start_date': start_date, 
    'end_minute': (duration / 60.0 + start_minute) % TS.MINUTES_PER_WEEK,
    'size': file_size,
    'duration_sec': duration
  }


def stream_name(list_in, start_minute, duration_minute):
  """ Get the stream name from list and start minute over a given duration. """
  duration_sec = duration_minute * 60.0

  # The start_minute above is in absolute terms, not those relative to the file.
  start_offset = start_minute - list_in[0]['start_minute']
  first_file = list_in[0]['name']
  callsign, unix_time = re.findall('(\w*)-(\d+)', first_file)[0]

  # print unix_time, start_minute
  fname = "%s/%s-%d_%d.mp3" % (misc.DIR_SLICES, callsign, int(unix_time) + start_offset * 60, duration_minute)
  return fname


def mp3_info(byte):
  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

  samp_rate = freqTable[(byte & 0x0f) >> 2]
  bit_rate = brTable[byte >> 4]
  pad_bit = (byte & 0x3) >> 1

  try:
    # from http://id3.org/mp3Frame
    frame_size = (144000 * bit_rate / samp_rate) + pad_bit

  except:
    return False, False, False, False

  return frame_size, samp_rate, bit_rate, pad_bit

def get_audio_format(fname):
  """ 
  Determines the audio format of an fname 
  and returns where the start of
  the audio block is.
  """
  f = open(fname, 'rb')
  audio_format = None, None

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
        audio_format = FORMAT_AAC, pos
        break

      elif b1 == 0xfb or b1 == 0xfa:
        # In order to see if it's an mp3 or not we read the next byte
        # and try to get the stats on the frame
        b = ord(f.read(1))
        frame_size, samp_rate, bit_rate, pad_bit = mp3_info(b)

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
            f.close()
            audio_format = FORMAT_MP3, pos
            break

      f.seek(pos + 1)

  f.close()
  return audio_format


def signature(fname, blockcount=-1):
  audio_format = DB.get('format') 

  if not audio_format:
    audio_format, start = get_audio_format(fname)

    if audio_format:
      logging.info("Setting this stream's audio format as %s" % audio_format)
      DB.set('format', audio_format)

    else:
      logging.warn("Can't determine type of file for %s." % fname)
      return False
  
  if audio_format == FORMAT_MP3: 
    return mp3_signature(fname, blockcount)

  if audio_format == FORMAT_AAC:
    return aac_signature(fname, blockcount)

# using http://wiki.multimedia.cx/index.php?title=ADTS
def aac_signature(fname, blockcount=-1):
  f = open(fname, 'rb')

  # This tries to find the first readable SOF bytes
  while True:
    if ord(f.read(1)) == 0xff:
      if ord(f.read(1)) & 0xf6 == 0xf0:
        f.seek(f.tell() - 2)
        break
    
  frame_number = 0
  header_size = 7

  sig_size = 12
  ignore_size = 3
  frame_sig = []
  start_byte = []
  first_header_seen = True

  while blockcount != 0:

    blockcount -= 1

    frame_start = f.tell()

    block = f.read(header_size)

    if not block or len(block) < header_size:
      break

    b0, b1, b2, b3, b4, b5, b6 = [ord(byte) for byte in block[:header_size]]

    # b0       b1       b2       b3       b4       b5       b6
    # AAAAAAAA AAAABCCD EEFFFFGH HHIJKLMM MMMMMMMM MMMOOOOO OOOOOOPP 
    # 84218421 84218421 84218421 84218421 84218421 84218421 84218421
    #                                                       
    #
    # A     12  syncword 0xFFF, all bits must be 1 
    # B     1   MPEG Version: 0 for MPEG-4, 1 for MPEG-2
    # C     2   Layer: always 0
    # D     1   protection absent, Warning, set to 1 if there is no CRC and 0 if there is CRC
    # E     2   profile, the MPEG-4 Audio Object Type minus 1 
    # F     4   MPEG-4 Sampling Frequency Index (15 is forbidden) 
    # G     1   private bit, guaranteed never to be used by MPEG, set to 0 when encoding, ignore when decoding
    # H     3   MPEG-4 Channel Configuration (in the case of 0, the channel configuration is sent via an inband PCE) 
    # I     1   originality, set to 0 when encoding, ignore when decoding
    # J     1   home, set to 0 when encoding, ignore when decoding
    # K     1   copyrighted id bit, the next bit of a centrally registered copyright identifier, set to 0 when encoding, ignore when decoding
    # L     1   copyright id start, signals that this frame's copyright id bit is the first bit of the copyright id, 
    #           set to 0 when encoding, ignore when decoding
    # M     13  frame length, this value must include 7 or 9 bytes of header length: 
    #           FrameLength = (ProtectionAbsent == 1 ? 7 : 9) + size(AACFrame)
    # O     11  Buffer fullness
    # P     2   Number of AAC frames (RDBs) in ADTS frame minus 1, for maximum compatibility always use 1 AAC frame per ADTS frame
    # Q     16  CRC if protection absent is 0 
    

    # A and C (yes this is 0xf SIX and 0xf ZERO)
    if b0 != 0xff or (b1 & 0xf6 != 0xf0): 
      logging.warn('[aac] %s Broken at frame#%d' % (fname, frame_number))
      break

    #
    # For all intents and purposes this doesn't seem to be a real
    # heavy indicator for our calculations ... since in practice 
    # the radio streams will be all stereo.
    #
    # freq = b2 >> 2 & 0xf
    # channels = (b2 & 1) << 2 | b3 >> 6
    protect_absent = b1 & 1
    frame_length = (b3 & 3) << 11 | b4 << 3 | b5 >> 5
    # frame_count = (b6 & 3) + 1

    f.read(ignore_size)
    sig_data = f.read(sig_size)

    # print binascii.b2a_hex(sig_data), c, frame_number, fname
    frame_sig.append(sig_data)
    start_byte.append(frame_start)

    frame_number += 1 
    f.read(frame_length - header_size - sig_size - ignore_size)
 
  f.close()

  info = stream_info(fname)
  DB.register_stream(info)
  return frame_sig, start_byte


def mp3_signature(fname, blockcount=-1):
  """
  Opens an mp3 file, find all the blocks, the byte offset of the blocks, and if they
  are audio blocks, construct a signature mapping of some given beginning offset of the audio
  data ... this is intended for stitching.
  """
  frame_sig = []
  start_byte = []
  first_header_seen = False
  header_attempts = 0

  #
  # Looking at the first 16 bytes of the payload yield a rate that is 99.75% unique
  # as tested over various corpi ranging from 1,000,000 - 7,000,000 blocks.
  #
  # There's an additional precautions of looking for a string of 4 matches which
  # mitigates this even further
  #
  read_size = 8

  f = open(fname, 'rb')
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

        frame_size, samp_rate, bit_rate, pad_bit = mp3_info(b)

        if not frame_size:
          continue

        if not first_header_seen:
          first_header_seen = True

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        sig = f.read(read_size)

        frame_sig.append(sig)

        start_byte.append(frame_start)

        # Move forward the frame f.read size + 4 byte header
        throw_away = f.read(frame_size - (read_size + 4))

      # ID3 tag for some reason
      elif header == '\x49\x44':
        # Rest of the header
        throw_away = f.read(4)

        #
        # Quoting http://id3.org/d3v2.3.0
        #
        # The ID3v2 tag size is encoded with four bytes where the most significant bit 
        # (bit 7) is set to zero in every byte, making a total of 28 bits. The zeroed 
        # bits are ignored, so a 257 bytes long tag is represented as $00 00 02 01.
        #
        candidate = struct.unpack('>I', f.read(4))[0]
        size = ((candidate & 0x007f0000) >> 2 ) | ((candidate & 0x00007f00) >> 1 ) | (candidate & 0x0000007f)
        
        f.read(size)

      # ID3 TAG -- 128 bytes long
      elif header == '\x54\x41':
        # We've already read 2 so we can go 126 forward
        f.read(126)

      elif len(header) == 1:
        # We are at the end of file, but let's just continue.
        next

      elif first_header_seen or header_attempts > MAX_HEADER_ATTEMPTS:
        import binascii
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

  info = stream_info(fname, guess_time=FRAME_LENGTH * len(frame_sig))
  DB.register_stream(info)
  return frame_sig, start_byte


def our_mime():
  our_format = DB.get('format') or 'mp3'
  
  if our_format == 'mp3': return 'audio/mpeg'
  if our_format == 'aac': return 'audio/aac'

def get_time(fname):
  """
  Determines the duration of an audio file by doing some estimates based on the offsets

  Returns the audio time in seconds.
  """
  # If we don't have a bitrate yet we assume 128
  bitrate = int(DB.get('bitrate') or 128)
  if os.path.exists(fname):
    return os.path.getsize(fname) / (bitrate * (1000 / 8))

  return None


def stitch_and_slice_process(file_list, start_minute, duration_minute):
  """ The process wrapper around stitch_and_slice to do it asynchronously. """
  name_out = stream_name(file_list, start_minute, duration_minute) 

  if os.path.isfile(name_out):
    file_size = os.path.getsize(name_out)
    # A "correct" filesize should be measured as more than 65% of what the
    # math would be. So first we can guess that.
    bitrate = int(DB.get('bitrate') or 128)
    estimate = (bitrate / 8) * (duration_minute * 60) * (10 ** 3)

    if 0.65 * estimate < file_size:
      logging.info("[stitch] File %s found" % name_out)
      return None

  # We presume that there is a file list we need to make 
  stitched_list = stitch(file_list, force_stitch=True)

  if stitched_list and len(stitched_list) > 1:
    info = stream_info(stitched_list)

  else:
    logging.warn("Unable to stitch file list")
    return False

  # print info, start_minute
  # After we've stitched together the audio then we start our slice
  # by figuring our the start_minute of the slice, versus ours
  start_slice = start_minute #max(start_minute - info['start_minute'], 0)

  # Now we need to take the duration of the stream we want, in minutes, and then
  # make sure that we don't exceed the length of the file.
  duration_slice = min(duration_minute, start_slice + info['duration_sec'] / 60.0)

  sliced_name = list_slice(
    list_in=stitched_list, 
    name_out=name_out,
    start_sec=start_slice*60.0, 
    duration_sec=duration_slice*60.0,
  )

  return None


def stitch_and_slice(file_list, start_minute, duration_minute):
  """
  Given a file_list in a directory and a duration, this function will seek out
  adjacent files if necessary and serialize them accordingly, and then return the
  file name of an audio slice that is the combination of them.
  """
  from multiprocessing import Process
  slice_process = Process(target=stitch_and_slice_process, args=(file_list, start_minute, duration_minute, ))
  slice_process.start()


def list_slice(list_in, name_out, duration_sec, start_sec):
  """
  Takes some stitch list, list_in and then create a new one based on the start and end times 
  by finding the closest frames and just doing an extraction.
  """
  pid = misc.change_proc_name("%s-audioslice" % misc.config['callsign'])

  out = open(name_out, 'wb+')
  
  # print 'slice', duration_sec, start_sec
  for ix in range(0, len(list_in)):
    item = list_in[ix]

    # get the regular map
    siglist, offset = signature(item['name'])

    if ix == len(list_in) - 1:
      frame_end = min(int(math.ceil(duration_sec / FRAME_LENGTH)), len(offset) - 1)

    else:
      frame_end = len(offset) - 1

    if ix == 0:
      frame_start = min(max(int(math.floor(start_sec / FRAME_LENGTH)), 0), len(offset) - 1)
      duration_sec -= (item['duration_sec'] - start_sec)

    else:
      frame_start = item['start_offset']
      duration_sec -= item['duration_sec'] 

    # try and get the mp3
    fin = cloud.get(item['name'])

    if fin:
      fin.seek(offset[frame_start])
      out.write(fin.read(offset[frame_end] - offset[frame_start]))
      fin.close()

    # If we fail to get the mp3 file then we can suppose that
    # the map file is bad so we just wince and remove it.
    else:
      os.unlink(item['name'])
      logging.warn("Unable to find %s's corresponding mp3, deleting" % item['name'])

  out.close()

  # If we failed to do anything this is a tragedy
  # and we just dump the file
  #
  # We take files under some really nominal threshold as being invalid.
  if os.path.getsize(name_out) < 1000:
    logging.warn("Unable to create %s - no valid slices" % name_out)
    os.unlink(name_out)


def stitch(file_list, force_stitch=False):
  """
  Takes a list of files and then attempt to seamlessly stitch them 
  together by looking at their signature checksums of the data payload in the blocks.
  """

  duration = 0

  start_index = 0

  while start_index < len(file_list):
    first = file_list[start_index]
    res = cloud.get(first['name'], do_open=False)
    start_index += 1
    if res: break

  if start_index == len(file_list):
    logging.error("Unable to find any files matching in the list for stitching.")
    return False

  siglist, offset = signature(first['name'])

  # print first, start_index
  first['siglist'] = siglist
  first['offset'] = offset

  args = [{
    'name': first['name'], 
    # We don't let the first byte be the beginning because we want
    # to produce valid files.
    'start_byte': first['offset'][0], 
    'start_offset': 0,
    'end_byte': first['offset'][-2],
    'start_minute': 0,
    'duration_sec': (len(first['offset']) - 1) * FRAME_LENGTH
  }]

  duration += len(first['offset']) * FRAME_LENGTH

  for second in file_list[start_index:]:
    res = cloud.get(second['name'], do_open=False)

    if not res:
      continue

    siglist, offset = signature(second['name'])

    second['siglist'] = siglist
    second['offset'] = offset

    isFound = True

    pos = -1
    try:
      while True:
        pos = second['siglist'].index(first['siglist'][-2], pos + 1)

        isFound = True
        for i in xrange(5, 1, -1):
          if second['siglist'][pos - i + 2] != first['siglist'][-i]:
            isFound = False
            logging.warn("Indices @%d do not match between %s and %s" % (pos, first['name'], second['name']))
            break

        # If we got here it means that everything matches
        if isFound: break 
        else: continue

    except Exception as exc:
      logging.warn("Cannot find indices between %s and %s" % (first['name'], second['name']))
      pos = 1

    if isFound or force_stitch:
      args.append({
        'name': second['name'], 
        'start_byte': second['offset'][pos], 
        'end_byte': second['offset'][-2],
        'start_offset': pos,
        'start_minute': (pos * FRAME_LENGTH) / 60.0,
        'duration_sec': (len(second['offset']) - pos - 1) * FRAME_LENGTH
      })

      duration += (len(second['offset']) - pos - 1) * FRAME_LENGTH
      first = second
      continue

    break

  return args

