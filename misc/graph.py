#!/usr/bin/python
import json
import sys

# Snagged from http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
def getTerminalSize():
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

    ### Use get(key[, default]) instead of a try/catch
    #try:
    #    cr = (env['LINES'], env['COLUMNS'])
    #except:
    #    cr = (25, 80)
  return int(cr[1]), int(cr[0])

width, height = getTerminalSize()

stats = json.loads(sys.stdin.read())

parts = ((width - 4) / 24) * 24

region_list = sorted([ (row[4], row[5]) for row in stats['streams']])
#print region_list
ptr = 0

minutes_per_day = 60 * 24
flag = False

mapper = [0] * 10080
for start, stop in region_list:
  for i in range(start, stop):
    mapper[i] += 1

def ts_row(parts):
  last_hr = -1 
  sys.stdout.write("+-")
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

ts_row(parts)

last_hr = -1 
start = 0
for day in ['M', 'T', 'W', 'T', 'F', 'S', 'S']:
  sys.stdout.write("%s " % day)

  for ix in range(parts):
    lower = start + (minutes_per_day * ix / parts)
    upper = start + (minutes_per_day * (ix + 1) / parts)
    mid = (upper - lower) / 2 + lower

    hr = 48 * ix / parts

    if mapper[mid] == 1:
      sys.stdout.write('*')
    elif mapper[mid] == 2:
      sys.stdout.write('=')
    elif mapper[mid] == 3:
      sys.stdout.write('E')
    elif mapper[mid] > 3:
      sys.stdout.write('#')
    else:
      #print lower,upper,region_list[ptr]
      if hr != last_hr:
        sys.stdout.write('.')
      else:
        sys.stdout.write(' ')

    last_hr = hr

  sys.stdout.write("|\n")
  start += minutes_per_day

ts_row(parts)
