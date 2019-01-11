#!/usr/bin/python3

import dbus
import time

modem = 0
def next_iface():
  global modem
  print("Trying modem {}".format(modem))
  proxy = bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/{}'.format(modem))
  iface = {
    'location': dbus.Interface(proxy, dbus_interface='org.freedesktop.ModemManager1.Modem.Location'),
    'time': dbus.Interface(proxy, dbus_interface='org.freedesktop.ModemManager1.Modem.Time')
  }
  modem += 1 
  return iface

def get_location():
  global modem
  while modem < 4:
    try: 
      location = iface['location'].GetLocation()
      networktime = iface['time'].GetNetworkTime()
      return { 'location': location, 'time': networktime }

    except:
      iface = next_iface()
      
