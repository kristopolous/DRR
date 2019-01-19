#!/usr/bin/python3
import re
import lib.db as DB
import logging
import time
import json
from datetime import datetime, timedelta
from dateutil import parser as dt_parser
from lxml import etree

# Everything is presumed to be weekly and on the minute
# scale. We use this to do wrap around when necessary
MINUTES_PER_WEEK = 10080
ONE_HOUR_SECOND = 60 * 60
ONE_DAY_MINUTE = 60 * 24
ONE_DAY_SECOND = 60 * ONE_DAY_MINUTE
WEEKDAY_LIST = ['mon','tue','wed','thu','fri','sat','sun']

def now(offset_sec=0):
  # Returns the time.time() equivalent given the offset of the station 
  return datetime.utcnow() + timedelta(minutes=get_offset(), seconds=offset_sec)


def uptime():
  import lib.misc as misc
  return int(unixtime('uptime') - misc.start_time)

def unixtime(what=''):
  # This is used instead of time.time() in order to make this more testable 
  return time.time()

def to_minute(unix_time):
  # Takes a given unix time and finds the week minute corresponding to it. 
  if type(unix_time) is int:
    unix_time = datetime.fromtimestamp(unix_time)

  return unix_time.weekday() * (24.0 * 60) + unix_time.hour * 60 + unix_time.minute + (unix_time.second / 60.0)

def frac_date(what):
  second = 0
  suffix = ''

  # accomodate for things preceding the time
  all_parts = what.split(' ')
  what = all_parts.pop()

  if what.lower().endswith('m'):
    suffix = what[-2:]
    what = what[:-2]

  parts = what.split(':')
  for piece in parts:
    second = (second * 60) + float(piece)
 
  # If we get something like 7pm, then
  # we need to scale this up.  By counting
  # the number of pieces, we can scale up
  # appropriately.
  second *= (60 ** (3 - len(parts)))

  hour = int(second / 3600)
  second -= hour * 3600

  minute = int(second / 60)
  second -= minute * 60

  all_parts.append("{0:d}:{1:02d}:{2:03.2f}{3:s}".format(hour, minute, second,suffix))

  return ' '.join(all_parts)

# probably not right but we'll see
def extract_time(in_str):
  start = re.sub('[+_-]', ' ', in_str)
  return start.split(' ').pop()

def str_to_time(in_str):
  start = re.sub('[+_-]', ' ', in_str)
  try:
    start = frac_date(start)
    dt = dt_parser.parse(start)
    
    # This silly library will take "monday" to mean NEXT monday, not the
    # one that just past.  What a goofy piece of shit this is.
    if dt > now():
      # Furthermore if we started with a number, say 11pm and its now 1am,
      # and this library is trying to get 11pm a week from now, we actually
      # want 11pm as in 2 hours ago, not as in 6 days and 2 hours ago.
      # So I guess we check the first letter for being a number.
      if start[0] >= "0" and start[0] <= "9":
        dt -= timedelta(days=1)
      else:
        dt -= timedelta(days=7)

  except:
    return None

  return dt


def duration_parse(duration_string):
  # Duration is expressed either in minutes or in \d+hr\d+ minute
  re_minute = re.compile('^(\d+)(?:min|m|)$')
  re_hr_solo = re.compile('^([\d\.]+)hr$', re.I)
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
      duration_min = float(res.groups()[0]) * 60

    else:
      res = re_hr_min.match(duration_string)

      if res:
        duration_min = int(res.groups()[0]) * 60 + int(res.groups()[1])

  return duration_min


def name_to_unix(name):
  if isinstance(name, (int, float)):
    name = str(int(round(name)))

  return int(time.mktime(time.strptime(name, "%Y%m%d%H%M")))

def ts_to_name(ts=None, with_seconds=False):
  # This goes from a datetime to a name. Since python has so many different confusing
  # time types, we have to be a bit clever about this to keep our code sane. Also we shouldn't
  # necessarily be suggesting any type for our conversion.
  if not ts: ts = now()

  if isinstance(ts, (int, float)):
    ts = datetime.fromtimestamp(ts).timetuple()

  if type(ts) is datetime:
    ts = ts.timetuple()

  if with_seconds:
    return time.strftime("%Y%m%d%H%M_%S", ts)

  return time.strftime("%Y%m%d%H%M", ts)

def sec_now(offset_sec=0):
  # Returns the unix time with respect to the timezone of the station being recorded.
  # Accepts an optional offset_sec to forward the time into the future.
  return int((now(offset_sec=offset_sec)).strftime('%s'))


def minute_now():
  # Returns the mod 10080 week minute with respect to the timezone of the station being recorded. 
  return to_minute(now())


def to_utc(day_str, hour):
  # Takes the nominal weekday (sun, mon, tue, wed, thu, fri, sat)
  # and a 12 hour time hh:mm [ap]m and converts it to our absolute units
  # with respect to the timestamp in the configuration file.
  if hour.endswith('min'):
    return int(hour[:-3])

  try:
    day_number = WEEKDAY_LIST.index(day_str[0:3].lower())
    hour = frac_date(hour)
    dt_struct = dt_parser.parse(hour)

  except:
    return None

  return (day_number * 24 + dt_struct.hour) * 60 + dt_struct.minute + dt_struct.second / 60.0 


def get_offset(force=False):
  # Contacts the goog, giving a longitude and lattitude and gets the time 
  # offset with regard to the UTC.  There's a sqlite cache entry for the offset.
  # Returns an int second offset.
  import lib.misc as misc

  # If we are testing this from an API level, then we don't
  # have a database
  if misc.IS_TEST: return 0

  offset_backup = DB.get('offset')
  offset = DB.get('offset', expiry=ONE_HOUR_SECOND * 4)

  if not offset or force:
    from urllib.request import urlopen

    when = int(unixtime())

    api_key = misc.config['_private']['misc']['timezonedb_key']
    url = "http://api.timezonedb.com/v2.1/get-time-zone?key={}&by=position&lat={}&lng={}".format(api_key, misc.config['lat'], misc.config['long'])

    try:
      stream = urlopen(url)
      data = stream.read().decode('utf8').split("\n")[1]
      xml = etree.fromstring(data)
      offset = xml.xpath('gmtOffset')
      opts = {'status': 'OK', 'offset': int(offset[0].text) }

    except Exception as exc:
      print(exc)
      opts = {'status': None}

    if opts['status'] == 'OK': 
      offset = opts['offset'] / 60
      logging.info("Found Offset: {}".format(offset))
      DB.set('offset', offset)

    else:
      # use the old one
      DB.set('offset', offset_backup)
      offset = offset_backup

  return int(float(offset))

