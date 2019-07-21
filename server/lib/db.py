#!/usr/bin/python3
import threading
import logging
import sqlite3
import time
import os
import sys
from datetime import timedelta
from threading import Lock

g_db_count = 0
g_params = {}
g_lock = Lock();

# This is a way to get the column names after grabbing everything
# I guess it's also good practice
_SCHEMA = {
  'kv': [
     ('id', 'INTEGER PRIMARY KEY'),
     ('key', 'TEXT UNIQUE'),
     ('value', 'TEXT'),
     ('namespace', 'TEXT'),
     ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
   ],
  'streams': [
     ('id', 'INTEGER PRIMARY KEY'), 
     ('name', 'TEXT UNIQUE'),
     ('start_unix', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
     ('end_unix', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
     ('start_minute', 'REAL DEFAULT 0'),
     ('end_minute', 'REAL DEFAULT 0'),
     ('week_number', 'INTEGER DEFAULT 0'),
     ('size', 'INTEGER DEFAULT 0'),
     # This is the meta-information that links
     # this file to the next one in the stream
     # (Presuming that there's only one of course)
     ('current_block', 'INTEGER DEFAULT 0'),
     ('next_file_name', 'TEXT'),
     ('next_file_block', 'INTEGER DEFAULT 0'),
     ('hidden', 'INTEGER default null')
   ]
}

# Ok so if column order or type changes, this isn't found ... nor
# are we doing formal migrations where you can roll back or whatever
# because way too fancy ...
def upgrade():
  my_set = __builtins__['set']
  db = connect()

  for table, schema in list(_SCHEMA.items()):
    existing_schema = db['c'].execute('pragma table_info(%s)' % table).fetchall()
    existing_column_names = [str(row[1]) for row in existing_schema]

    our_column_names = [row[0] for row in schema]

    # print table, existing_column_names, our_column_names

    to_add = my_set(our_column_names).difference(my_set(existing_column_names))

    # These are the things we should add ... this can be an empty set, that's fine.
    for key in to_add:
      # 
      # sqlite doesn't support adding things into positional places (add column after X)
      # they just get tacked on at the end ... which is fine - you'd have to rebuild 
      # everything to achieve positional columns - that's not worth it - we just always 
      # tack on at the end as a policy in our schema and we'll be fine.
      #
      # However, given all of that, we still need the schema
      #
      our_schema = schema[our_column_names.index(key)][1]
      # print 'alter table %s add column %s %s' % (table, key, our_schema)
      db['c'].execute('alter table %s add column %s %s' % (table, key, our_schema))
      db['conn'].commit()

    to_remove = my_set(existing_column_names).difference(my_set(our_column_names))

    if len(to_remove) > 0:
      our_schema = ','.join(["%s %s" % (key, klass) for key, klass in schema])
      our_columns = ','.join(our_column_names)

      drop_column_sql = """
      CREATE TEMPORARY TABLE my_backup(%s);
      INSERT INTO my_backup SELECT %s FROM %s;
      DROP TABLE %s;
      CREATE TABLE %s(%s);
      INSERT INTO %s SELECT %s FROM my_backup;
      DROP TABLE my_backup;
      """ % (our_schema, our_columns, table, table,    table, our_schema, table, our_columns)

      for sql_line in drop_column_sql.strip().split('\n'):
        db['c'].execute(sql_line)

      db['conn'].commit()

def map(row_list, table, db=None):
  # Using the schema of a table, map the row_list to a list of dicts.
  mapped = []
  my_schema = schema(table, db)

  if not row_list:
    return row_list

  if type(row_list[0]) is str:
    row_list = [row_list]

  for row in row_list:
    mapped_row = {}
    for ix in range(len(my_schema)):
      mapped_row[my_schema[ix]] = row[ix]

    mapped.append(mapped_row)

  return mapped


def all(table, field_list='*', sort_by='id'):
  # Returns all entries from the sqlite3 database for a given table. 

  column_count = 1
  if type(field_list) is not str:
    column_count = len(field_list)
    field_list = ','.join(field_list)

  query = run('select %s from %s order by %s asc' % (field_list, table, sort_by))
  if column_count is 1 and field_list != '*':
    return [record[0] for record in query.fetchall()]

  else:
    return [record for record in query.fetchall()]


def schema(table, db=None):
  existing_schema = run('pragma table_info(%s)' % table, db=db).fetchall()
  if existing_schema:
    return [str(row[1]) for row in existing_schema]

  return None


def disconnect(what):
  what['conn'].close()
  pass  
  
def connect(db_file=None):
  # A "singleton pattern" or some other fancy $10-world style of maintaining 
  # the database connection throughout the execution of the script.
  # Returns the database instance.
  global g_db_count

  if not db_file:
    db_file = 'config.db'

  #
  # We need to have one instance per thread, as this is what
  # sqlite's driver dictates ... so we do this based on thread id.
  #
  # We don't have to worry about the different memory sharing models here.
  # Really, just think about it ... it's totally irrelevant.
  #

  instance = {}

  if not os.path.exists(db_file):
    sys.stderr.write("Info: Creating db file %s\n" % db_file)

  conn = sqlite3.connect(db_file)
  instance.update({
    'conn': conn,
    'c': conn.cursor()
  })

  if db_file == 'config.db' and g_db_count == 0: 

    for table, schema in list(_SCHEMA.items()):
      dfn = ','.join(["%s %s" % (key, klass) for key, klass in schema])
      instance['c'].execute("CREATE TABLE IF NOT EXISTS %s(%s)" % (table, dfn))

    instance['conn'].commit()

  g_db_count += 1 

  return instance


def incr(key, value=1):
  # Increments some key in the database by some value.  It is used
  # to maintain statistical counters.

  try:
    run('update kv set value = value + ? where key = ?', args=(value, key, ))

  except Exception as exc:
    try:
      run('insert into kv(value, key) values(?, ?)', args=(value, key, ))
    except sqlite3.OperationalError as exc:
      logging.warn("Unable to increment key: %s", exc)
      pass


def set(key, value):
  # Sets (or replaces) a given key to a specific value.  
  # Returns the value that was sent.
  global g_params

  try:
    if value is None:
      res = run('delete from kv where key = ?', (key, ))
      
    else:
      # Let's just do two calls. Nobody else is accessing it right here I think
      # this is atomic enough.
      res = run('select id from kv where key = ?', (key, )).fetchone()
      if not res:
        run('insert into kv (key, value) values(?, ?)', (key, value))
        
      else:
        run('update kv set value = ? where key = ?', (value, key))

  except:
    logging.warn("[DB error] Couldn't set {} to {}".format(key, value))

  g_params[key] = value

  return value


def clear_cache():
  global g_params
  g_params = {}

def get(key, expiry=0, use_cache=True, default=None):
  # Retrieves a value from the database, tentative on the expiry. 
  # If the cache is set to true then it retrieves it from in-memory if available, otherwise
  # it goes out to the db. Other than directly hitting up the g_params parameter which is 
  # used internally, there is no way to invalidate the cache.
  global g_params

  # only use the cache if the expiry is not set.
  if use_cache and key in g_params and expiry == 0:
    if default and type(default) is int: 
      g_params[key] = int(g_params[key])

    return g_params[key]

  if expiry > 0:
    # If we let things expire, we first sweep for it
    res = run("select value, created_at from kv where key = '%s' and created_at >= datetime(current_timestamp, '-%d second')" % (key, expiry)).fetchone()
  else:
    res = run('select value, created_at from kv where key = ?', (key, )).fetchone()

  if res:
    if default and type(default) is int: 
      res = list(res)
      res[0] = int(res[0])

    g_params[key] = res[0]
    return res[0]

  else:
    # It's ok if this doesn't exist. SQLite likes to throw an error here
    try:
      run("delete from kv where key = '%s' and created_at < datetime(current_timestamp, '-%d second')" % (key, expiry))
    except Exception as inst:
      pass

  return default


def run(query, args=None, with_last=False, db=None):
  start = time.time()
  """
  if args is None:
    print "%d: %s" % (g_db_count, query)
  else:
    $print "%d: %s (%s)" % (g_db_count, query, ', '.join([str(m) for m in args]))
  """

  g_lock.acquire()
  if db is None:
    db = connect()

  res = None

  try:
    if args is None:
      res = db['c'].execute(query)
    else:
      res = db['c'].execute(query, args)

    db['conn'].commit()
    last = db['c'].lastrowid

    if db['c'].rowcount == 0:
      raise Exception("0 rows")

  except Exception as exc:
    raise exc

  finally:
    g_lock.release()

  if with_last:
    return (res, last)

  return res

def unregister_stream(name, do_all=False):
  # Deletes a stream by name, contingent on it existing only once 

  res = run('select id from streams where name = ?', (name, )).fetchall()

  if res and (len(res) == 1 or do_all):
    logging.debug("Removing our reference of %s" % name)
    res = run('delete from streams where id = %d' % res[0][0])

  else:
    logging.warn("Requested to remove reference of %s but couldn't find it." % name)

  return True


def register_stream(info):
  # Registers a stream as existing to be found later when trying to stitch and slice files together.
  # This is all that ought to be needed to know if the streams should attempt to be stitched. The input
  # info is grabbed from audio.stream_info(filename)
  name = info['name']
  start_unix = info['start_date']
  end_unix = info['start_date'] + timedelta(seconds=info['duration_sec']) 
  start_minute = float(info['start_minute'])
  end_minute = float(info['end_minute'])
  week_number = info['week_number']
  size = info['size']

  res = run('select id from streams where name = ?', (name, )).fetchone()

  # If something exists then we remove it and reinsert ... this is not as effecient
  # as an upsert with coalesce, but this is done on rare occasions in heavy workloads ...
  # so we don't really need to be entirely efficient about it.
  if res:
    unregister_stream(name, do_all=True)

  last = False
  try:
    res, last = run("""insert into streams 
    (name, start_unix, end_unix, start_minute, end_minute, week_number, size) values
    (   ?,          ?,        ?,            ?,          ?,           ?,    ?) """, 
    (name, start_unix, end_unix, start_minute, end_minute, week_number, size), with_last=True)

  except:
    logging.warn("Unable to insert a record with a name %s" % name)

  return last

