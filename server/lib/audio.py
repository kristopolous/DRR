#!/usr/bin/python -O
import os
import math
import gzip
import marshal
import re
import struct
import logging
import db as DB
import lib.misc as misc
import lib.file as cloud
import lib.ts as TS
from datetime import datetime, timedelta, date

# Most common frame-length ... in practice, I haven't 
# seen other values in the real world
FRAME_LENGTH = (1152.0 / 44100)

#
# Some stations don't start you off with a valid mp3 header
# (such as kdvs), so we have to just seek into the file
# and look for one.  This is the number of bytes we try.
# In practice, 217 appears to be enough, so we make it about
# ten times that and cross our fingers
#
MAX_HEADER_ATTEMPTS = 2048

def get_map(fname):
  """ Retrieves a map file associated with the mp3 """
  map_name = fname if fname.endswith('.map') else fname + '.map'

  if os.path.exists(map_name):
    f = gzip.open(map_name, 'r')
    ret = marshal.loads(f.read())
    f.close()
    return ret

  return None, None

    
def list_info(file_list):
  """ A version of the stream_info that accepts a list """
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
    print "Failure for '%s'" % fname
    raise Exception

  try:
    duration = guess_time if guess_time else get_time(fname) 

  except Exception as exc:
    # If we can't find a duration then we try to see if it's in the file name
    ts_re_duration = re.compile('_(\d*).mp3')
    ts = ts_re_duration.findall(fname)
    if ts:
      duration = int(ts[0]) * 60

  if type(duration) is not int:
    duration = 0

  return {
    # The week number 
    'week': start_date.isocalendar()[1], 
    'name': fname, 
    'start_minute': start_minute, 
    'start_date': start_date, 
    'end_minute': (duration / 60.0 + start_minute) % TS.MINUTES_PER_WEEK,
    'duration_sec': duration
  }


def stream_name(list_in, start_minute, duration_minute):
  duration_sec = duration_minute * 60.0

  first_file = list_in[0]['name']
  callsign, unix_time = re.findall('(\w*)-(\d+)', first_file)[0]

  return "slices/%s-%d_%d.mp3" % (callsign, int(unix_time) + start_minute * 60, duration_minute)


def crc(fname, blockcount=-1):
  """
  Opens an mp3 file, find all the blocks, the byte offset of the blocks, and if they
  are audio blocks, construct a crc32 mapping of some given beginning offset of the audio
  data ... this is intended for stitching.
  """
  # Simply make sure that there is a map associated with the
  # mp3.  Otherwise create one.
  map_name = fname if fname.endswith('.map') else fname + '.map'

  if only_check and os.path.exists(map_name):
    return True

  crc32, offset = get_map(fname)
  if crc32 is not None:
    return crc32, offset

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

  freqTable = [ 44100, 48000, 32000, 0 ]

  brTable = [
    0,   32,  40,  48, 
    56,  64,  80,  96, 
    112, 128, 160, 192, 
    224, 256, 320, 0
  ]

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

        samp_rate = freqTable[(b & 0x0f) >> 2]
        bit_rate = brTable[b >> 4]
        pad_bit = (b & 0x3) >> 1

        # from http://id3.org/mp3Frame
        try:
          frame_size = (144000 * bit_rate / samp_rate) + pad_bit

          # If there's a /0 error
        except:
          continue

        if not first_header_seen:
          first_header_seen = True

          # We try to record the CBR associated with this
          # stream
          if not DB.get('bitrate', use_cache=True):
            DB.set('bitrate', bit_rate)

        # Rest of the header
        throw_away = f.read(1)

        # Get the signature
        crc = f.read(read_size)

        frame_sig.append(crc)

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
  DB.register_stream(
    name=fname,
    week_number=info['week'],
    start_minute=int(info['start_minute']),
    end_minute=int(info['end_minute']),
    start_unix=info['start_date'],
    end_unix=info['start_date'] + timedelta(seconds=info['duration_sec'])
  )
  return frame_sig, start_byte


def get_time(fname):
  """
  Determines the duration of an audio file by doing some estimates based on the offsets

  Returns the audio time in seconds
  """
  map_name = fname + '.map'
  if os.path.exists(map_name):
    crc32, offset = get_map(map_name)
    return FRAME_LENGTH * len(offset)

  else:
    bitrate = int(DB.get('bitrate', use_cache=True))
    if os.path.exists(fname) and bitrate > 0:
      return os.path.getsize(fname) / (bitrate * (1000 / 8))


def stitch_and_slice_process(file_list, start_minute, duration_minute):
  """
  Given a file_list in a directory and a duration, this function will seek out
  adjacent files if necessary and serialize them accordingly, and then return the
  file name of an audio slice that is the combination of them.
  """
  name_out = stream_name(file_list, start_minute, duration_minute) 

  if os.path.isfile(name_out) and os.path.getsize(name_out) > 0:
    logging.info("[stitch] File %s found" % name_out)
    return None

  # We presume that there is a file list we need to make 
  stitched_list = stitch(file_list, force_stitch=True)

  if stitched_list and len(stitched_list) > 1:
    info = stream_info(stitched_list)

  else:
    logging.warn("Unable to stitch file list")
    return False

  # After we've stitched together the audio then we start our slice
  # by figuring our the start_minute of the slice, versus ours
  start_slice = max(start_minute - info['start_minute'], 0)

  # Now we need to take the duration of the stream we want, in minutes, and then
  # make sure that we don't exceed the length of the file.
  duration_slice = min(duration_minute, start_slice + info['duration_sec'] / 60.0)

  sliced_name = list_slice(
    list_in=stitched_list, 
    name_out=name_out,
    start_sec=start_slice*60, 
    duration_sec=duration_slice*60,
  )

  return None


def stitch_and_slice(file_list, start_minute, duration_minute):
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

  for ix in range(0, len(list_in)):
    item = list_in[ix]

    # get the regular map
    crc32, offset = crc(item['name'])

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

    # try and get the mp3 referred to by the map file
    fin = cloud.get(item['name'].replace('.map',''))

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
  together by looking at their crc32 checksums of the data payload in the blocks.
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

  crc32, offset = crc(first['name'])

  # print first, start_index
  first['crc32'] = crc32
  first['offset'] = offset

  args = [{
    'name': first['name'], 
    'start_byte': 0, 
    'start_offset': 0,
    'end_byte': first['offset'][-1],
    'start_minute': 0,
    'duration_sec': (len(first['offset']) - 1) * FRAME_LENGTH
  }]

  duration += len(first['offset']) * FRAME_LENGTH

  for second in file_list[start_index:]:
    res = cloud.get(second['name'], do_open=False)

    if not res:
      continue

    crc32, offset = crc(second['name'])

    second['crc32'] = crc32
    second['offset'] = offset

    isFound = True

    pos = -1
    try:
      while True:
        pos = second['crc32'].index(first['crc32'][-2], pos + 1)

        isFound = True
        for i in xrange(5, 1, -1):
          if second['crc32'][pos - i + 2] != first['crc32'][-i]:
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
        'start_minute': pos * FRAME_LENGTH,
        'duration_sec': (len(second['offset']) - pos - 1) * FRAME_LENGTH
      })

      duration += (len(second['offset']) - pos - 1) * FRAME_LENGTH
      first = second
      continue

    break

  return args


