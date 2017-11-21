#!/usr/bin/python3
import os
from math import ceil
import re
import struct
import logging
from time import sleep
import lib.db as DB
import lib.ts as TS
from datetime import datetime, timedelta
import traceback

# Most common frame-length ... in practice, I haven't 
# seen other values in the real world.
#
# TODO: This implicitly opens a database instance ... not a good idea
_FRAME_LENGTH = (1152.0 / 44100) #DB.get('samp', default=44100))
_TS_RE = re.compile('(\w*)-(\d*)[.|_]')

_FORMAT_MP3 = 'mp3'
_FORMAT_AAC = 'aac'
_LASTFORMAT = None

#
# Some stations don't start you off with a valid mp3 header
# (such as kdvs), so we have to just seek into the file
# and look for one.  This is the number of bytes we try.
# In practice, 217 appears to be enough, so we make it about
# ten times that and cross our fingers.
#
_MAX_HEADER_ATTEMPTS = 32000

def list_info(file_list):
  # A version of the stream_info that accepts a list. 
  info = stream_info(file_list[0]['name'])

  # Some things are the same such as the
  # week, start_minute, start_date
  info['duration_sec'] = 0
  for item in file_list:
    info['duration_sec'] += item['duration_sec']

  info['end_minute'] = (info['duration_sec'] / 60.0 + info['duration_sec']) % TS.MINUTES_PER_WEEK

  return info


def stream_info(file_name, skip_size=False):
  # Determines the date the thing starts,
  # the minute time it starts, and the duration
  #
  # If you do skip_size = True then you avoid any i/o 
  # and have everything determined solely by the name.
  # This means that some values returned will be set to 
  # None

  if type(file_name) is list:
    return list_info(file_name)

  info = _TS_RE.findall(file_name)

  # 0 byte files can throw this thing off
  # if it's set to None
  duration_sec = 0
  start_minute = None
  start_date = None
  end_minute = None
  callsign = None

  if info:
    info = info[0]
    callsign = info[0]

    # We have two formats here ... one is unix time 
    # and the other is a much more readable time.  We will determine
    # whether it's UNIX time by seeing if it's greater than 2**36, which
    # makes us not Y4147 compliant. Oh dear - better fix this sometime
    # in the next 2100 years!
    unix_time = int(info[1])

    if unix_time > 2**36:
      unix_time = TS.name_to_unix(unix_time)  

    start_minute = TS.to_minute(unix_time)
    start_date = datetime.fromtimestamp(unix_time)

  else:
    logging.warn("Failure to find info for '%s'" % file_name)
    return None

  try:
    # Just skip over this if the skip_size is set
    if skip_size: raise Exception

    # If we don't have a bitrate yet we assume 128
    bitrate = int(DB.get('bitrate') or 128)

    if bitrate == 0:
      logging.warn("Bitrate is 0. This is a bug.")
      raise Exception

    file_size = os.path.getsize(file_name)

    # If our file size is zero that means that we hit a bug
    # trying to stitch this, so we raise and exception and 
    # try to reconstitute the file.
    if file_size == 0:
      logging.warn("File %s exists and is 0 bytes. Ignoring it for computation." % file_name)
      raise Exception

    duration_sec = file_size / (bitrate * (1000.0 / 8.0))

  except Exception as inst:
    file_size = None
    # If we can't find a duration then we try to see if it's in the file name
    ts_re_duration = re.compile('_(\d*).{4}')
    ts = ts_re_duration.findall(file_name)
    if ts:
      duration_sec = int(ts[0]) * 60.0

  if isinstance(duration_sec, (int, float)):
    end_minute = (duration_sec / 60.0 + start_minute) % TS.MINUTES_PER_WEEK

  return {
    'callsign': callsign,
    'week_number': start_date.isocalendar()[1], 
    'name': file_name, 
    'start_minute': start_minute, 
    'start_date': start_date, 
    'end_minute': end_minute,
    'size': file_size,
    'duration_sec': duration_sec
  }


def stream_name(list_in, absolute_start_minute, duration_minute, relative_start_minute=None):
  import lib.misc as misc
  # Get the stream name from list and start minute over a given duration. 
  duration_sec = duration_minute * 60.0

  # The start_minute above is in absolute terms, not those relative to the file.
  if not relative_start_minute:
    relative_start_minute = absolute_start_minute - list_in[0]['start_minute']

  first_file = list_in[0]['name']
  info = stream_info(first_file)
  ts = TS.ts_to_name(info['start_date'] + timedelta(minutes=relative_start_minute))
  
  # print '--offset', unix_time, start_minute, list_in[0]['start_minute'] , list_in
  fname = "%s/%s-%s_%d.mp3" % (misc.DIR_SLICES, info['callsign'], ts, duration_minute)
  return fname

# We need to be a bit fancy in determining our sample since there's
# plenty of weird false positives that arive from our heuristic methods
samp_distribution = {}
def samp_guess(samp):
  if DB.get('samp'): return True

  global samp_distribution

  # first to this amount is our winner
  cutoff = 10

  if samp not in samp_distribution:
    samp_distribution[samp] = 0

  samp_distribution[samp] += 1

  if samp_distribution[samp] > cutoff:
    DB.set('samp', samp)
    globals()['_FRAME_LENGTH'] = (1152.0 / samp)


def mp3_info(byte, b1):
  failCase = [ False, False, False, False ]

  mpegTable = [ 2, 1 ]
  layerTable = [ None, 3, 2, 1 ]
  
  sampTable = [  
    None,
    [ 44100, 48000, 32000, 0 ],
    [ 22050, 24000, 16000, 0 ]
  ]

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

  if mpeg is None or layer != 3: return failCase

  samp_rate = sampTable[mpeg][(byte & 0x0f) >> 2]
  bit_rate = brTable[mpeg][layer][byte >> 4]
  pad_bit = (byte & 0x3) >> 1

  if not bit_rate or not samp_rate: return failCase

  # from http://id3.org/mp3Frame
  frame_size = int((144000 * bit_rate / samp_rate) + pad_bit)

  return frame_size, samp_rate, bit_rate, pad_bit


def get_audio_format(file_name):
  # Determines the audio format of file_name and return 
  # where the start of the audio block is.
  if isinstance(file_name, str):
    is_stream = False 
    file_handle = open(file_name, 'rb')

  else:
    is_stream = True
    file_handle = file_name

  audio_format = None, None

  # mp3 blocks appear to be \xff\xfb | \x49\x44 | \x54\x41
  # aac is \xff(\xf6 == \xf0) ... 
  while True:
    pos = file_handle.tell()

    try:
      b0 = ord(file_handle.read(1))

    except:
      break

    if b0 == 0xff:
      b1 = ord(file_handle.read(1))

      if b1 & 0xf6 == 0xf0:
        audio_format = _FORMAT_AAC, pos
        break

      elif b1 >> 4 == 0xf:
        # In order to see if it's an mp3 or not we read the next byte
        # and try to get the stats on the frame
        b = ord(file_handle.read(1))
        frame_size, samp_rate, bit_rate, pad_bit = mp3_info(b, b1)

        # If there's a computed frame_size then we can continue
        if frame_size:
          # We try to move forward and see if our predictive 
          # next block works. 
          file_handle.seek(pos + frame_size)

          # If this is an mp3 file and that frame was valid, then
          # we should now be at the start of the next frame.
          b0, b1 = [byte for byte in file_handle.read(2)]

          if b0 == 0xff and b1 >> 4 == 0xf:
            # That's good enough for us
            file_handle.close()
            audio_format = _FORMAT_MP3, pos
            break

      file_handle.seek(pos + 1)

  if not is_stream: file_handle.close()
  return audio_format


def signature(fname, blockcount=-1, depth=1):
  global _LASTFORMAT
  audio_format = DB.get('format') 

  if not audio_format:
    audio_format, start = get_audio_format(fname)

    if audio_format:
      logging.info("Setting this stream's audio format as %s" % audio_format)
      DB.set('format', audio_format)

    else:
      logging.warn("Can't determine type of file for %s." % fname)
      return None, None
  
  block = None
  if audio_format == _FORMAT_AAC:
    sig, block = aac_signature(fname, blockcount)

  # We permit the idea that a file can be a false positive. But we do not
  # permit the idea that a file can be a false positive and correctly register
  # over some number of sequential blocks (currently set at whatever the
  # constant is below).
  if audio_format == _FORMAT_MP3 or not block or len(block) < 5: 
    sig, block = mp3_signature(fname, blockcount)

    if len(block) > 0 and audio_format == _FORMAT_AAC:
      DB.set('format', _FORMAT_MP3)
      DB.clear_cache()

  # Stream formats can change actually.
  if len(block) < 5:
    tryformat = _FORMAT_AAC
    if audio_format == _FORMAT_AAC: tryformat = _FORMAT_MP3
    DB.set('format', tryformat)
    DB.clear_cache()

    # Make sure we don't foolishly recurse
    if depth == 1:
      return signature(fname, blockcount, depth + 1)

    else:
      # Otherwise if we fail to find anything upon our change-format desperation
      # move, we should return this as the none type to be handled appropriately.
      return None, None

  _LASTFORMAT = audio_format

  return sig, block


def aac_find_frame(file_handle, file_name):
  # This tries to find the first readable SOF bytes
  start = file_handle.tell()
  while True:
    try:
      b0 = file_handle.read(1)
      """
      # oh great, fucking FLV
      if b0 == 'F' and file_handle.read(2) == 'LV':
        if flv_skip(f): break
      """

      if b0[0] == 0xff:
        if ord(file_handle.read(1)) & 0xf6 == 0xf0:
          file_handle.seek(file_handle.tell() - 2)
          return True
        else:
          file_handle.seek(-1, 1)

    except:
      logging.warn("[aac-sig] Could not find header. searched %d bytes in %s starting at %d" % (file_handle.tell() - start, file_name, start))
      traceback.print_stack()
      return False

# using http://wiki.multimedia.cx/index.php?title=ADTS
def aac_signature(file_name, blockcount=-1):
  is_stream = False
  start_pos = None

  if isinstance(file_name, str):
    file_handle = open(file_name, 'rb')

  else:
    # This means we can handle file pointers
    is_stream = True
    file_handle = file_name
    start_pos = file_handle.tell()

  if not aac_find_frame(file_handle, file_name): 
    return None, None
    
  frame_number = 0
  header_size = 7

  sig_size = 12
  ignore_size = 3
  frame_sig = []
  start_byte = []
  first_header_seen = True

  while blockcount != 0:

    blockcount -= 1

    frame_start = file_handle.tell()

    block = file_handle.read(header_size)

    if not block or len(block) < header_size:
      break

    b0, b1, b2, b3, b4, b5, b6 = [byte for byte in block[:header_size]]

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
      if not is_stream:

        if frame_number < 2:
          logging.warn("[aac] %s:%d False start" % (file_name, file_handle.tell()))
          file_handle.seek(frame_start + 1)

          # We second guess our format decision
          #DB.set('format', None)

          if not aac_find_frame(file_handle, file_name): 
            return None, None

          continue

        else:
          logging.warn('[aac] %s:%d Broken at frame#%d' % (file_name, file_handle.tell(), frame_number))

      break

    #
    # For all intents and purposes this doesn't seem to be a real
    # heavy indicator for our calculations ... since in practice 
    # the radio streams will be all stereo.
    #
    # freq = b2 >> 2 & 0xf
    # channels = (b2 & 1) << 2 | b3 >> 6
    # protect_absent = b1 & 1
    frame_length = (b3 & 3) << 11 | b4 << 3 | b5 >> 5
    # frame_count = (b6 & 3) + 1

    file_handle.read(ignore_size)
    sig_data = file_handle.read(sig_size)

    frame_sig.append(sig_data)
    start_byte.append(frame_start)

    frame_number += 1 
    file_handle.read(frame_length - header_size - sig_size - ignore_size)
 
  if not is_stream:
    file_handle.close()

  else:
    file_handle.seek(start_pos)

  return frame_sig, start_byte


def mp3_signature(file_name, blockcount=-1):
  # Opens an mp3 file, find all the blocks, the byte offset of the blocks, and if they
  # are audio blocks, construct a signature mapping of some given beginning offset of the audio
  # data ... this is intended for stitching.
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
  is_stream = False
  start_pos = None

  frame_size = None
  assumed_set = None
  attempt_set = None
  last_tell = None
  go_back = -1

  if isinstance(file_name, str):
    file_handle = open(file_name, 'rb')

  else:
    # This means we can handle file pointers
    file_handle = file_name
    is_stream = True
    start_pos = file_handle.tell()

  while blockcount != 0:

    if first_header_seen:
      blockcount -= 1

    else:
      header_attempts += 1 
      if header_attempts > 2:
        file_handle.seek(go_back, 1)

    frame_start = file_handle.tell()
    if frame_start == last_tell:
      file_handle.seek(last_tell + 1, 1)

    header = file_handle.read(2)
    if header and len(header) == 2:

      b1 = header[1]

      if header[0] == 0xff and (b1 >> 4) == 0xf:

        try:
          b = ord(file_handle.read(1))
          # If we are at the EOF
        except:
          break

        if frame_size and not assumed_set:
          attempt_set = [samp_rate, bit_rate, pad_bit]

        frame_size, samp_rate, bit_rate, pad_bit = mp3_info(b, b1)

        last_tell = file_handle.tell()

        if not frame_size:
          file_handle.seek(go_back, 1)
          go_back = -1

          continue

        samp_guess(samp_rate)

        # We make sure that we get the same set of samp_rate, bit_rate, pad_bit twice
        if not assumed_set and attempt_set == [samp_rate, bit_rate, pad_bit]:
          assumed_set = attempt_set
          attempt_set = False

        # This is another indicator that we could be screwing up ... 
        elif assumed_set and samp_rate != assumed_set[0] and bit_rate != assumed_set[1]:
          file_handle.seek(go_back, 1)
          continue


        if not first_header_seen:
          first_header_seen = True

        # Rest of the header
        throw_away = file_handle.read(1)

        # Get the signature
        sig = file_handle.read(read_size)
        frame_sig.append(sig)
        start_byte.append(frame_start)

        # Move forward the frame file_handle.read size + 4 byte header
        throw_away = file_handle.read(frame_size - (read_size + 4))

        if file_handle.tell() > 3:
          go_back = -3

      # ID3 tag for some reason
      elif header == '\x49\x44':
        # Rest of the header
        throw_away = file_handle.read(4)

        #
        # Quoting http://id3.org/d3v2.3.0
        #
        # The ID3v2 tag size is encoded with four bytes where the most significant bit 
        # (bit 7) is set to zero in every byte, making a total of 28 bits. The zeroed 
        # bits are ignored, so a 257 bytes long tag is represented as $00 00 02 01.
        #
        candidate = struct.unpack('>I', file_handle.read(4))[0]
        size = ((candidate & 0x007f0000) >> 2 ) | ((candidate & 0x00007f00) >> 1 ) | (candidate & 0x0000007f)
        
        file_handle.read(size)

      # ID3 TAG -- 128 bytes long
      elif header == '\x54\x41':
        # We've already read 2 so we can go 126 forward
        file_handle.read(126)

      elif len(header) == 1:
        # We are at the end of file, but let's just continue.
        next

      elif header_attempts > _MAX_HEADER_ATTEMPTS:
        if not is_stream:
          import binascii
          samp = DB.get('samp', default=44100)
          if type(samp) is str:
            logging.debug("OMG WHAT THE FUCK")
            samp = int(samp)

          logging.debug('[mp3-sig] %d[%d/%d]%s:%s:%s %s %d' % (len(frame_sig), header_attempts, _MAX_HEADER_ATTEMPTS, binascii.b2a_hex(header), binascii.b2a_hex(file_handle.read(5)), file_name, hex(file_handle.tell()), len(start_byte) * (1152.0 / DB.get('samp', default=44100)) / 60))

        # This means that perhaps we didn't guess the start correct so we try this again
        if len(frame_sig) == 1 and header_attempts < _MAX_HEADER_ATTEMPTS:
          logging.debug("[mp3-sig] False start -- trying again")

          # seek to the first start byte + 1
          file_handle.seek(start_byte[0] + 2)

          # discard what we thought was the first start byte and
          # frame signature
          start_byte = []
          frame_sig = []
          first_header_seen = False

          # Also our assumed set was probably wrong
          assumed_set = None

        else:
          break

      elif first_header_seen:
        header_attempts += 1 
        if header_attempts > 2:
          file_handle.seek(go_back, 1)
          go_back = -1

    else:
      break

  if not is_stream:
    file_handle.close()

  else:
    file_handle.seek(start_pos)

  return frame_sig, start_byte


def our_mime():
  our_format = DB.get('format') or 'mp3'
  
  if our_format == 'aac': return 'audio/aac'

  # Default to mp3
  return 'audio/mpeg'


def stitch_and_slice_process(file_list, relative_start_minute, duration_minute):
  # The process wrapper around stitch_and_slice to do it asynchronously. 
  name_out = stream_name(file_list, relative_start_minute=relative_start_minute, duration_minute=duration_minute, absolute_start_minute=None) 

  if os.path.isfile(name_out):
    file_size = os.path.getsize(name_out)
    # A "correct" filesize should be measured as more than 65% of what the
    # math would be. So first we can guess that.
    bitrate = int(DB.get('bitrate') or 128)
    estimate = (bitrate / 8) * (duration_minute * 60) * (10 ** 3)

    if 0.75 * estimate < file_size:
      logging.info("[stitch] File %s found" % name_out)
      return None

  # We presume that there is a file list we need to make 
  stitched_list = stitch(file_list, force_stitch=True)
  logging.info("stitched")
  logging.info(stitched_list)
  logging.info("%d %d" % (len(file_list), len(stitched_list)))

  # We see if it was correct, on the condition that it had to be made
  if stitched_list and (len(stitched_list) == len(file_list) == 1) or (len(stitched_list) > 1 and len(file_list) > 1):
    info = stream_info(stitched_list)

  else:
    logging.warn("Unable to stitch file list")
    return None

  # After we've stitched together the audio then we start our slice
  # by figuring our the relative_start_minute of the slice, versus ours
  start_slice = relative_start_minute #max(start_minute - info['start_minute'], 0)

  # Now we need to take the duration of the stream we want, in minutes, and then
  # make sure that we don't exceed the length of the file.
  duration_slice = min(duration_minute, start_slice + info['duration_sec'] / 60.0)

  # print "startslice---", start_slice, relative_start_minute
  sliced_name = list_slice(
    list_in=stitched_list, 
    name_out=name_out,
    start_sec=start_slice * 60.0, 
    duration_sec=duration_slice * 60.0,
  )

  return None


def stitch_and_slice(file_list, start_minute, duration_minute):
  # Given a file_list in a directory and a duration, this function will seek out
  # adjacent files if necessary and serialize them accordingly, and then return the
  # file name of an audio slice that is the combination of them.
  #from multiprocessing import Process
  from threading import Thread
  slice_process = Thread(name='sitch-slice-%s' % (TS.ts_to_name(), ), target=stitch_and_slice_process, args=(file_list, start_minute, duration_minute))
  slice_process.daemon = True
  slice_process.start()


def list_slice_stream(start_info, start_sec):
  import lib.cloud as cloud
  # This is part of the /live/time feature ... this streams files hopping from one to the next
  # in a live manner ... it constructs things while running ... hopping to the next stream in real time.
  #pid = misc.change_proc_name("%s-audiostream" % misc.config['callsign'])
  block_count = 0

  current_info = start_info

  # get the regular map so we know where to start from
  siglist, offset = signature(current_info['name'])
  start_frame = min(max(int(start_sec / _FRAME_LENGTH), 0), max(len(offset) - 1, 0))
  start_byte = offset[start_frame]

  while True:
    stream_handle = cloud.get(current_info['name'])
    stream_handle.seek(start_byte)
    sig, offset = signature(stream_handle)
    logging.debug("opening %s %d %d" % (current_info['name'], current_info['size'], stream_handle.tell()) )

    # After the initial start offset we should start looking at all
    # fugure files from the first byte.
    start_byte = 0

    # This helps us determine when we are at EOF ... which
    # we basically define as a number of seconds without any
    # valid read.
    times_none = 0
    block_count = 0
    read_size = 0

    while True:
      # So we want to make sure that we only send out valid, 
      # non-corrupt mp3 blocks that start and end
      # at reasonable intervals.
      if offset and len(offset) > 1:
        read_size = offset[1] - offset[0]
        offset.pop(0)

        block = stream_handle.read(read_size)
        block_count += 1
        times_none = 0 
        yield block

      else:  
        times_none += 1
        if times_none > 20:
          break
    
        elif times_none > 0:
          #print stream_handle.tell(), current_info['size'], times_none, len(block)
          # See if there's a next file that we can immediately go to
          next_info, offset = cloud.get_next(current_info)
          if next_info: 
            break

        # We wait 1/2 second and then try this process again, hopefully
        # the disk has sync'd and we have more data
        sleep(0.5)
        sig, offset = signature(stream_handle)

      
    logging.debug("closing %s %d %d %d %d" % (current_info['name'], current_info['size'], stream_handle.tell(), block_count, (stream_handle.tell() - start_byte) / (128000 / 8) / 60.0))
    pos = stream_handle.tell() 
    stream_handle.close()

    # If we are here that means that we ran out of data on our current
    # file.  The first things we should do is see if there is a next file
    next_info, offset = cloud.get_next(current_info)

    if next_info:

      # If there is we find the stitching point
      args = stitch([current_info, next_info], force_stitch=True)
      logging.debug('next file {} -> {}:{}'.format(current_info['name'], next_info['name'], offset))

      # We make it our current file
      current_info = next_info

      # Now we can assume that our args[1] is going to have all
      # the information pertaining to where the new file should pick
      # up from - all we really need is the start_byte
      if len(args) == 2:
        start_byte = args[1]['start_byte'] 
        # print "Starting at ", start_byte

      else:
        logging.warn("Live stitching failed")
        break

    else:
      # Otherwise we have to bail
      break


def list_slice(list_in, name_out, duration_sec, start_sec=0, do_confirm=False):
  import lib.cloud as cloud
  # Takes some stitch list, list_in and then create a new one based on the start and end times 
  # by finding the closest frames and just doing an extraction.
  #
  # Setting the duration as None is equivalent to a forever stream 
  #pid = misc.change_proc_name("%s-audioslice" % misc.config['callsign'])

  out = open(name_out, 'wb+')
  buf_confirm = None
  
  for ix in range(0, len(list_in)):
    item = list_in[ix]

    # get the regular map
    siglist, offset = signature(item['name'])

    if ix == len(list_in) - 1:
      frame_end = min(int(ceil(duration_sec / _FRAME_LENGTH)), len(offset) - 1)

    else:
      frame_end = len(offset) - 1

    if ix == 0:
      frame_start = min(max(int(start_sec / _FRAME_LENGTH), 0), len(offset) - 1)
      duration_sec -= (item['duration_sec'] - start_sec)

    else:
      frame_start = item['start_offset']
      duration_sec -= item['duration_sec'] 

    # try and get the mp3
    fin = cloud.get(item['name'])

    if fin:
      fin.seek(offset[frame_start])

      if do_confirm and buf_confirm:
        fin.seek(-16, 1)
        buf = fin.read(16)
        if buf != buf_confirm:
          logging.warn("Slicing error at %d of %s" % (fin.tell(), item['name']))

      # print 'off---',frame_end, frame_start, len(offset)
      try:
        buf = fin.read(offset[frame_end] - offset[frame_start])
      
        out.write(buf)

      except:
        logging.warn("Trying to read frames in %s that don't exist. Total frame count is %d while I'm trying to get %d and %d" % (item['name'], len(offset), frame_end, frame_start))


      if do_confirm:
        buf_confirm = buf[-16]

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
  import lib.cloud as cloud
  # Takes a list of files and then attempt to seamlessly stitch them 
  # together by looking at their signature checksums of the data payload in the blocks.
  duration = 0

  start_index = 0

  # This makes sure we have all the files on disk that we are looking
  # for by getting them from the cloud if necessary.
  while start_index < len(file_list):
    first = file_list[start_index]
    res = cloud.get(first['name'], do_open=False)
    start_index += 1
    if res: break

  # I can't really figure out what this code is about but I do know that it will fail
  # in cases where there's only one file to slice.  So there's a small check to make 
  # it ok for that case
  if start_index == len(file_list) and len(file_list) > 1:
    logging.error("Unable to find any files matching in the list for stitching.")
    return None

  siglist, offset = signature(first['name'])

  # print first, start_index
  first['siglist'] = siglist
  first['offset'] = offset

  end_byte = first['offset'][0]
  if len(first['offset']) > 2:
    end_byte = first['offset'][-2]

  else:
    logging.warn("%s is only %d frames" % (first['name'], len(offset)))

  args = [{
    'name': first['name'], 
    # We don't let the first byte be the beginning because we want
    # to produce valid files.
    'start_byte': first['offset'][0], 
    'start_offset': 0,
    'end_byte': end_byte,
    'start_minute': 0,
    'duration_sec': (len(first['offset']) - 1) * _FRAME_LENGTH
  }]

  duration += len(first['offset']) * _FRAME_LENGTH

  for second in file_list[start_index:]:
    res = cloud.get(second['name'], do_open=False)

    if not res:
      continue

    siglist, offset = signature(second['name'])

    second['siglist'] = siglist
    second['offset'] = offset
    
    # This happens if the file is corrupt or we otherwise
    # can't find the signature.  That means we can't stitch
    # these two files and should skip it.
    if siglist is None and offset is None: 
      continue

    is_found = True

    pos = -1
    try:
      while True:
        # The pos will be the same frame in the second stream as the first.
        pos = second['siglist'].index(first['siglist'][-2], pos + 1)

        is_found = True
        for i in range(5, 1, -1):
          if second['siglist'][pos - i + 2] != first['siglist'][-i]:
            is_found = False
            logging.warn("Indices @%d do not match between %s and %s" % (pos, first['name'], second['name']))
            break

        # If we got here it means that everything matches
        if is_found: break 
        else: continue

    except Exception as exc:
      logging.warn("Cannot find indices between %s and %s" % (first['name'], second['name']))
      pos = 1

    if is_found or force_stitch:
      # Since the pos was the same frame, if we use that then we essentially
      # use the same frame twice ... so we need to start one ahead of it.  The
      # easiest way to do this is just to increment the pos var.
      if is_found:
        pos += 1
        """
        import binascii

        print "----"
        for i in xrange(-4, 4):
          if i < 2:
            p1 = binascii.b2a_hex(first['siglist'][i - 2])

            if i == 0:
              p1 += '*'

          else:
            p1 = ''

          print "%s %s" % (binascii.b2a_hex(second['siglist'][pos + i]), p1)
        print args 
        """

      end_byte = second['offset'][0]
      if len(second['offset']) > 2:
        end_byte = second['offset'][-2]

      else: 
        logging.warn("%s is only %d frames" % (second['name'], len(second['offset'])))

      if len(second['offset']) < pos:
        logging.warn("Unable to find %d blocks in the file %s. Probably the wrong type inferenced." % (pos, second['name']))

      else:
        args.append({
          'name': second['name'], 
          'start_byte': second['offset'][pos], 
          'end_byte': end_byte,
          'start_offset': pos,
          'start_minute': (pos * _FRAME_LENGTH) / 60.0,
          'duration_sec': (len(second['offset']) - pos - 1) * _FRAME_LENGTH
        })

        duration += (len(second['offset']) - pos - 1) * _FRAME_LENGTH

      first = second
      continue

    break

  return args

