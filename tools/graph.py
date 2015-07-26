#!/usr/bin/python -O
"""
Given a stats query, this generates an ascii art chart which shows how good the coverage is of 
the station over a week modulus.  This helps test the healthiness of the stream and the 
server's connection to the stream.  The way to invoke this is as follows:

$ ./server_query.py -q stats -c [callsign, such as kpcc] | ./graph.py

         +-0----1----2----3----4----5----6----7----8----9----10---11---12---13---14---15---16---17---18---19---20---21---22---23---+
2015-07-09 .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .* . |
2015-07-10 .  . .* . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  .**  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . |
2015-07-11 .  . .  . .  . .  . .  . .  . .  . .* . .  . .  . .  . .  . .* . .  . .  . ** . .  . .  . .  . .  . .  . .  . .  . .* . |
2015-07-12 .  . .  . .  . .  . .  . . *. .  . .  . .  . . ** . ** .  . .  . .  . .  . .  . .  . .  . .  . .  .**  .*.  . .  . .  * |
2015-07-13 .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . . *. .  . .  . .  . .  . .  * .****.**.*** .**  . .  .** ** |
2015-07-14 .  . .* . .  . . ** . ** .*** .**. *  * .**.*.**.*.* . .* .**  . .* * .*** *  . * ***. *.****. ** .*** * ** .*** . .* . |
2015-07-15 .  . .*****  * .  ***  .** *. .  * .  * .* . . *. .* *****.** *. .  . .  .******************** ************************ |
2015-07-16 .******************************************* ****************************. ********* .********************************* |
2015-07-17 *************************************************************************************** .*.  . ** . ***.*.  * ** . ** * |
2015-07-18 ** . .  * .  . .  . .  . .  * .  . .**. .  . .  . .  . .  * .* . .  . .  . .**. .  . .  *************************.******|
2015-07-19 .****************** *************************************************************************************************** |
2015-07-20 .**************************************************************************************** ***********************.***** |
2015-07-21 .*************************************************************************************=****************=*************** |
2015-07-22 **********.******************** *********************************************************** *************************** |
2015-07-23 .***********************=****** **************************************************************************************. |
2015-07-24 *=***********************************************=**********.  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . .  . |
         +-0----1----2----3----4----5----6----7----8----9----10---11---12---13---14---15---16---17---18---19---20---21---22---23---+

         kcrw coverage: 54.3576388889 %

$

This tells us that we are getting pretty poor time coverage over the period that we are archiving. 
As of the writing of this, this is acceptable since this is pretty early in the dev time.  

Now without further ado, here's the code.
"""

import time
import re
import json
import sys
from datetime import datetime

# Snagged from http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
def getTerminalSize():
  """ 
  We would ideally like to print a graph at the precision of the users current terminal.  
  This allows us to do that.
  """
  import os

  env = os.environ
  def ioctl_GWINSZ(fd):
    try:
      import fcntl, termios, struct, os
      cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
    '1234'))

    except:
      return

    return cr

  cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
  if not cr:
    try:
      fd = os.open(os.ctermid(), os.O_RDONLY)
      cr = ioctl_GWINSZ(fd)
      os.close(fd)

    except:
      pass

  if not cr:
    cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

  return int(cr[1]), int(cr[0])


def ts_row(parts):
  """ Prints out a header row """

  last_hr = -1 
  sys.stdout.write("         +-")
  flag = False
  for ix in range(parts):
    hr = 24 * ix / parts
    if hr == last_hr:
      if not flag:
        sys.stdout.write("-")
      else:
        flag = False

    else:
      sys.stdout.write("%d" % hr)
      last_hr = hr
      if hr > 9:
        flag = True

  sys.stdout.write("+\n")

minutes_per_day = 60 * 24
width, height = getTerminalSize()
parts = ((width - 10) / 24) * 24
region_map = {}

stats = json.loads(sys.stdin.read())

callsign = stats['config']['callsign']

# Break the stats down into a per-day list.
for row in stats['streams']:
  day = row[2].split(' ')[0]

  if day not in region_map: 
    region_map[day] = []

  region_map[day].append(row)

# Then populate each day in a list, sorted by the time.
for key, value in region_map.items():
  region_map[key] = sorted([ (int(round(row[4])) % minutes_per_day, int(round(row[5])) % minutes_per_day) for row in value])

# Start with an aesthetic space and draw our header
print
ts_row(parts)

coverage = 0 
total = 0
last_hr = -1 

# Make sure we go through the dates in order
for day in sorted(region_map.keys()):
  region = region_map[day]

  # Create a map for this day and then populate it using the ranges
  mapper = [0] * minutes_per_day
  for start, stop in region:
    for i in range(start, stop):
      mapper[i] += 1

  # Here's how we compute the total coverage
  coverage += len(filter(lambda x: x != 0, mapper))
  total += minutes_per_day

  # Print the day we are considering
  sys.stdout.write("%s " % day)

  for ix in range(parts):
    lower = minutes_per_day * ix / parts
    upper = minutes_per_day * (ix + 1) / parts
    mid = int((upper - lower) / 2 + lower)

    # This indicates 30 minute breakpoints (48 units per day)
    hr = 48 * ix / parts

    """
    Ideally we should see a row of asterisks. 
    Seeing anything else is actually an "error" because 
    we shouldn't be multi-recording any region.
    """  
    if mapper[mid] == 1:
      sys.stdout.write('*')
    elif mapper[mid] == 2:
      sys.stdout.write('=')
    elif mapper[mid] > 2:
      sys.stdout.write('#')
    else:
      if hr != last_hr:
        sys.stdout.write('.')
      else:
        sys.stdout.write(' ')

    last_hr = hr

  # Round off the row aesthetically
  sys.stdout.write("|\n")

# End with another referential header row and the total coverage
ts_row(parts)
print "\n         %s coverage: %f%%\n" % (callsign, 100 * (float(coverage) / total))
