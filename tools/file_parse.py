#!/usr/bin/python3 
import sys
import lib.audio as audio

for file_name in sys.argv[1:]:
  print("%s:" % file_name)
  print(audio.stream_info(file_name))
  sig, block = audio.signature(file_name)
  print({'block_count': len(block), 'format': audio._LASTFORMAT})

