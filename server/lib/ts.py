#!/usr/bin/python -O
import re
import db as DB
import logging
from datetime import datetime, timedelta, date

# Everything is presumed to be weekly and on the minute
# scale. We use this to do wrap around when necessary
MINUTES_PER_WEEK = 10080
ONE_DAY = 60 * 60 * 24

def to_minute(unix_time):
  """ Takes a given unix time and finds the week minute corresponding to it. """
  if type(unix_time) is int:
    unix_time = datetime.fromtimestamp(unix_time)

  return unix_time.weekday() * (24 * 60) + unix_time.hour * 60 + unix_time.minute

def sec_now(offset_sec=0):
  """ 
  Returns the unix time with respect to the timezone of the station being recorded.
  
  Accepts an optional offset_sec to forward the time into the future
  """
  return int((datetime.utcnow() + timedelta(seconds=offset_sec, minutes=get_offset())).strftime('%s'))

def minute_now():
  """ Returns the mod 10080 week minute with respect to the timezone of the station being recorded """
  return to_minute(datetime.utcnow() + timedelta(minutes=get_offset()))

def to_utc(day_str, hour):
  """
  Takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
  and a 12 hour time hh:mm [ap]m and converts it to our absolute units
  with respect to the timestamp in the configuration file
  """
  global g_config

  try:
    day_number = ['mon','tue','wed','thu','fri','sat','sun'].index(day_str.lower())

  except Exception as exc:
    return False

  local = day_number * (60 * 24)

  time_re_solo = re.compile('(\d{1,2})([ap])m', re.I)
  time_re_min = re.compile('(\d{1,2}):(\d{2})([ap])m', re.I)

  time = time_re_solo.match(hour)
  if time:
    local += int(time.groups()[0]) * 60

  else:
    time = time_re_min.match(hour)

    if time:
      local += int(time.groups()[0]) * 60
      local += int(time.groups()[1])

  if not time:
    return False

  if time.groups()[-1] == 'p':
    local += (12 * 60)

  return local


def get_offset(force=False):
  """
  Contacts the goog, giving a longitude and lattitude and gets the time 
  offset with regard to the UTC.  There's a sqlite cache entry for the offset.

  Returns an int second offset
  """

  offset = DB.get('offset', expiry=ONE_DAY)
  if not offset or force:

    when = int(time.time())

    api_key = 'AIzaSyBkyEMoXrSYTtIi8bevEIrSxh1Iig5V_to'
    url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%d&key=%s" % (g_config['lat'], g_config['long'], when, api_key)
   
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
