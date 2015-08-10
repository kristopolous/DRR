#!/usr/bin/python -O
import re

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
