#!/usr/bin/python -O
import sys
import lib.misc as misc
import lib.ts as TS

data = sys.stdin.readlines()[0].split(' ')
print TS.to_utc(data[0], data[1])
