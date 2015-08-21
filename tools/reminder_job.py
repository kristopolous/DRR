#!/usr/bin/python -O
import re
import os
import argparse
import ConfigParser
import lib.misc as misc
import lib.db as DB
import time
import sys

def find_requests_and_send_mail(config):
  os.chdir(os.path.dirname(os.path.realpath(__file__)))
  db = DB.connect(db_file='../db/main.db')
  now = time.time()
  what_we_be_done_with = db['c'].execute('select * from reminders where end_time < %d' % now).fetchall()

  for row in DB.map(what_we_be_done_with, 'reminders', db=db):
    row['link'] = "http://indycast.net/%s/slices/%s_%d" % ( row['station'], time.strftime("%Y%m%d%H%M", time.gmtime(row['start_time'] - row['offset'] * 60)), (row['end_time'] - row['start_time']) / 60)

    if len(row['notes']):
      row['link'] += '/%s_on_%s' % (re.sub('[^\w]', '_', row['notes']).strip('_'), row['station'])

    row['link'] += '.mp3'

    email = do_template(template_file='email_reminder_template.txt', settings=row)
    res = misc.send_email(config=config, who=row['email'], subject=email['subject'], body=email['body'])
    db['c'].execute('delete from reminders where id = %d' % row['id'])
    db['conn'].commit()

  return None


def do_template(template_file, settings):

  def repl(match):
    alt = None
    expr = match.group(1).strip()
    tokenList = expr.split('|')
    token = tokenList[0]

    if len(tokenList) > 1:
      alt = tokenList[1]

    if token in settings:
      if settings[token]:
        return settings[token]

      elif alt:
        return alt

    return 'NO VARIABLE: %s' % token

  if not os.path.exists(template_file):
    raise Exception("%s file wasn't found." % template_file)

  with open(template_file, 'r') as template_file:
    template_raw = template_file.read()

    template_rows = template_raw.split('\n')
    subject_line = template_rows[0]

    body = '\n'.join(template_rows[1:])

    return {
      'subject': re.sub('{{([\s\w]*)}}', repl, subject_line),
      'body': re.sub('{{([\s\w]*)}}', repl, body)
    } 


config = misc.mail_config()
find_requests_and_send_mail(config)

