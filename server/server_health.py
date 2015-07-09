#!/usr/bin/python -O
import sqlite3
import time

g_db = {}

def db_connect():
  """
  a "singleton pattern" or some other fancy $10-world style of maintaining 
  the database connection throughout the execution of the script.

  Returns the database instance
  """

  global g_db

  if 'conn' not in g_db:
    conn = sqlite3.connect('../db/main.db')
    g_db = {'conn': conn, 'c': conn.cursor()}

  return g_db

db = db_connect()

cycle_time = 60 * 60 * 12

while True:
  # retrieve a list of the active stations
  station_list = db['c'].execute('select * from stations where active == 1')

  for station in station_list:
    print station

  time.sleep(cycle_time)
