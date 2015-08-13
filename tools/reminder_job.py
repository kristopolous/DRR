#!/usr/bin/python -O
import re
import os
import requests
import argparse
import ConfigParser
import lib.misc as misc
import lib.db as DB
import time

# Taken from https://bradgignac.com/2014/05/12/sending-email-with-python-and-the-mailgun-api.html
def send_email(config, who, subject, body):
  key = config['base_key']
  request_url = "%s/%s" % (config['base_url'].strip('/'), 'messages')

  print request_url
  request = requests.post(request_url, auth=('api', key), data={
    'from': 'Indycast Reminders <reminders@indycast.net>',
    'to': who,
    'subject': subject,
    'text': body
  })

  return request


def find_requests(config):
  db = DB.connect('../db/main.db')
  now = time.time()
  print now
  what_we_be_done_with = db['c'].execute('select * from reminders where (end_time + offset * 60) < %d' % now).fetchall()

  for row in DB.map(what_we_be_done_with, 'reminders'):
    row['link'] = "http://indycast.net/%s/streams/%s-%s_%d.mp3" % ( row['station'], row['station'], time.strftime("%Y%m%d%H%M", time.gmtime(row['start_time'])), (row['end_time'] - row['start_time']) / 60)

    email = do_template(template_file='email_reminder_template.txt', settings=row)
    res = send_email(config=config, who='kristopolous@yahoo.com', subject=email['subject'], body=email['body'])
    db['c'].execute('delete from reminders where id = %d' % row['id'])
    db['conn'].commit()

  return None

def do_template(template_file, settings):

  def repl(match):
    token = match.group(1).strip()
    if token in settings:
      return settings[token]

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


def setup():
  cfg = os.environ.get('CLOUD_CFG')

  os.chdir(os.path.dirname(os.path.realpath(__file__)))

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
  args = parser.parse_args()

  if args.config is None:
    print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
    sys.exit(-1)

  cloud_config = ConfigParser.ConfigParser()
  cloud_config.read(args.config)

  return misc.config_section_map('Mailgun', cloud_config)

config = setup()

find_requests(config)

