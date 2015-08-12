#!/usr/bin/python -O
import re
import os
import requests
import argparse
import ConfigParser
import lib.misc as misc

# Taken from https://bradgignac.com/2014/05/12/sending-email-with-python-and-the-mailgun-api.html
def send_email(who, subject, body):
  key = 'YOUR API KEY HERE'

  request_url = 'https://api.mailgun.net/v3/indycast.net'

  request = requests.post(request_url, auth=('api', key), data={
    'from': 'do-not-reply@indycast.net',
    'to': who,
    'subject': subject,
    'text': body
  })

  return request


def do_template(template_file, settings):

  def repl(match):
    token = match.group(1).strip()
    if token in settings:
      return settings[token]

    return ''

  if not os.path.exists(template_file):
    raise Exception("%s file wasn't found." % template_file)

  with open(template_file, 'r') as template_file:
    template_raw = template_file.read()

    template_rows = template_raw.split('\n')
    subject_line = template_rows[0]

    body = '\n'.join(template_rows[1:])

    return {
      'subject': re.sub('{{([\s\w]*)}}', repl, subject_line)
      'body': re.sub('{{([\s\w]*)}}', repl, body)
    } 


do_template(template_file='email_reminder_template.txt', settings={'notes': 'some show', 'link': 'somelink', 'begin': 'begin', 'end': 'end', 'date': 'date'})

cfg = os.environ.get('CLOUD_CFG')

os.chdir(os.path.dirname(os.path.realpath(__file__)))

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default=cfg, help="cloud credential file to use")
args = parser.parse_args()

if args.config is None:
  print "Define the cloud configuration location with the CLOUD_CFG environment variable or using the -c option"
  sys.exit(-1)
