#!/usr/bin/python -O
import re
import requests
import ConfigParser
import lib.misc as misc

# Taken from https://bradgignac.com/2014/05/12/sending-email-with-python-and-the-mailgun-api.html
def send_email():
  key = 'YOUR API KEY HERE'
  recipient = 'YOUR EMAIL HERE'

  request_url = 'https://api.mailgun.net/v3/indycast.net'
  request = requests.post(request_url, auth=('api', key), data={
    'from': 'hello@example.com',
    'to': recipient,
    'subject': 'Hello',
    'text': 'Hello from Mailgun'
  })


def do_template(settings):

  def repl(match):
    token = match.group(1).strip()
    if token in settings:
      return settings[token]

    return ''

  with open('email_reminder_template.txt', 'r') as template_file:
    template_raw = template_file.read()
    template_processed = re.sub('{{([\s\w]*)}}', repl, template_raw)
    print template_processed

do_template({'notes': 'some show', 'link': 'somelink', 'begin': 'begin', 'end': 'end', 'date': 'date'})
