#!/usr/bin/python -O
import re
import db as DB
import logging
import time
import json
import misc 
from datetime import datetime, timedelta, date

import socket

#
# This is needed to force ipv4 on ipv6 devices. It's sometimes needed
# if there isn't a clean ipv6 route to get to the big wild internet.
# In these cases, a pure ipv6 route simply will not work.  People aren't
# always in full control of every hop ... so it's much safer to force
# ipv4 then optimistically cross our fingers.
#
origGetAddrInfo = socket.getaddrinfo
getAddrInfoWrapper = misc.getAddrInfoWrapper
socket.getaddrinfo = getAddrInfoWrapper

import urllib2
import urllib

# Everything is presumed to be weekly and on the minute
# scale. We use this to do wrap around when necessary
MINUTES_PER_WEEK = 10080
ONE_DAY_MINUTE = 60 * 24
ONE_DAY_SECOND = 60 * ONE_DAY_MINUTE

def now(offset_sec=0):
  """ Returns the time.time() equivalent given the offset of the station """
  return datetime.utcnow() + timedelta(minutes=get_offset(), seconds=offset_sec)


def uptime():
  return int(unixtime('uptime') - misc.start_time)

def unixtime(what=''):
  """ This is used instead of time.time() in order to make this more testable """
  return time.time()

def to_minute(unix_time):
  """ Takes a given unix time and finds the week minute corresponding to it. """
  if isinstance(unix_time, (int, long)):
    unix_time = datetime.fromtimestamp(unix_time)

  return unix_time.weekday() * (24.0 * 60) + unix_time.hour * 60 + unix_time.minute + (unix_time.second / 60.0)

def duration_parse(duration_string):
  # Duration is expressed either in minutes or in \d+hr\d+ minute
  re_minute = re.compile('^(\d+)(?:min|)$')
  re_hr_solo = re.compile('^(\d+)hr$', re.I)
  re_hr_min = re.compile('^(\d+)hr(\d+).*$', re.I)

  duration_min = None

  res = re_minute.match(duration_string)
  if res:
    duration_min = int(res.groups()[0])

    # This means that the input is just numeric.
    # This is fine for now, but we use this to construct prose such as
    # "So and so is a xxx show recorded" ... in this case, a unit is
    # nice to have there for legibility purposes.  Since we are doing
    # with our parsing of the string, we can just ammend the unit
    # to the end
    if re.match('^(\d+)$', duration_string):
      duration_string += 'min'

  else:
    res = re_hr_solo.match(duration_string)

    if res:
      duration_min = int(res.groups()[0]) * 60

    else:
      res = re_hr_min.match(duration_string)

      if res:
        duration_min = int(res.groups()[0]) * 60 + int(res.groups()[1])

  return duration_min


def name_to_unix(name):
  if isinstance(name, (int, long)):
    name = str(name)

  return int(time.mktime(time.strptime(name, "%Y%m%d%H%M")))

def ts_to_name(ts=None):
  """
  This goes from a datetime to a name. Since python has so many different confusing
  time types, we have to be a bit clever about this to keep our code sane. Also we shouldn't
  necessarily be suggesting any type for our conversion.
  """
  if not ts: ts = now()

  if type(ts) is datetime:
    ts = ts.timetuple()

  return time.strftime("%Y%m%d%H%M", ts)

def sec_now(offset_sec=0):
  """ 
  Returns the unix time with respect to the timezone of the station being recorded.
  
  Accepts an optional offset_sec to forward the time into the future.
  """
  return int((now(offset_sec=offset_sec)).strftime('%s'))


def minute_now():
  """ Returns the mod 10080 week minute with respect to the timezone of the station being recorded. """
  return to_minute(now())


def to_utc(day_str, hour):
  """
  Takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
  and a 12 hour time hh:mm [ap]m and converts it to our absolute units
  with respect to the timestamp in the configuration file.
  """
  if hour.endswith('min'):
    return int(hour[:-3])

  try:
    day_number = ['mon','tue','wed','thu','fri','sat','sun'].index(day_str.lower())

  except Exception as exc:
    return None

  local = day_number * (60 * 24)

  time_re_solo = re.compile('^(\d{1,2})([ap]m|)$', re.I)
  time_re_min = re.compile('^(\d{1,2}):(\d{2})([ap]m|)', re.I)
  time_re_sec = re.compile('^(\d{1,2}):(\d{2}):(\d{2})([ap]m|)', re.I)

  my_time = time_re_solo.match(hour)
  if my_time:
    hr = int(my_time.groups()[0])
    local += hr * 60

  else:
    my_time = time_re_min.match(hour)

    if my_time:
      hr = int(my_time.groups()[0])
      local += hr * 60
      local += int(my_time.groups()[1])

    else:
      my_time = time_re_sec.match(hour)

      if my_time:
        hr = int(my_time.groups()[0])
        local += hr * 60
        local += int(my_time.groups()[1])
        # store seconds as fractional monutes
        local += float(my_time.groups()[2] / 60)

  if not my_time:
    return None

  # time is tricky if the hr is 12
  ampm = my_time.groups()[-1]
  if hr == 12:
    # 12AM is actually 1 hour BEFORE 1AM
    if ampm == 'am': local -= (12 * 60)

    # If it's 12PM then we don't need to do
    # the math below.
  elif my_time.groups()[-1] == 'pm':
    local += (12 * 60)

  return local


def get_offset(force=False):
  """
  Contacts the goog, giving a longitude and lattitude and gets the time 
  offset with regard to the UTC.  There's a sqlite cache entry for the offset.

  Returns an int second offset.
  """

  # If we are testing this from an API level, then we don't
  # have a database
  if misc.IS_TEST: return 0

  offset = DB.get('offset', expiry=ONE_DAY_SECOND)
  if not offset or force:

    when = int(unixtime())

    api_key = 'AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
    url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%d&key=%s" % (misc.config['lat'], misc.config['long'], when, api_key)
   
    stream = urllib2.urlopen(url)
    data = stream.read()
    opts = json.loads(data)

    if opts['status'] == 'OK': 
      logging.info("Location: %s | offset: %s" % (opts['timeZoneId'], opts['rawOffset']))
      offset = (int(opts['rawOffset']) + int(opts['dstOffset'])) / 60
      DB.set('offset', offset)

    else:
      offset = 0

  return int(offset)

