# Installation

To run the server, you need the things listed in the [bootstrap](https://github.com/kristopolous/DRR/blob/master/bootstrap.sh) file ( don't worry, this is a very simple file )

Your OS of choice should have these in their own terms - remember this is intended to be run on a server somewhere.

# Overview

There's three things of interest here:

  1. indy_server.py
  1. configs/
  1. server_query.py

## indy_server.py

This is a single process which, when run on a server

 * maintains podcast, stream, and download requests coming in
 * processes the audio from these requests
 * maintains the downloading and management of the underlying streams.

Normally you should be able to start up a server like this:

    $ ./indy_server.py -c configs/kpcc.txt 
    [kpcc-manager:16626] Starting
    [kpcc-webserver:16633] Starting
    Listening on 8930
    [kpcc-download:16634] Starting

Then you should get something like this:

    $ ps af
    ...
    16885 pts/14   Ss+    0:00 -zsh
    16626 pts/14   S+     0:00  \_ kpcc-manager                                           
    16633 pts/14   S+     0:00      \_ kpcc-webserver                                         
    16634 pts/14   Sl+    0:00      \_ kpcc-download  
    ...

If you want to shut things down, kill the manager pid

    $ kill 16885

Which is also stored in a pid file in the storage directory, which we will now go over.

In the storage directory you should see something like this:

 * config.db      - An sqlite3 database of intents and key/values
 * indy_server.py - A symlink'd copy of the server
 * pid-webserver  - A file that gets created and destroyed every time with the pid of the websever
 * pid-manager    - A file that gets created and destroyed every time with the pid of the manager
 * indycast.log   - A non-rolling eternal log
 * streams        - Recordings from the station in 15 minute blocks (this is configurable)
 * stitches       - Aggregations of streams to larger blocks which correspond to specific intents
 * slices         - Sliced versions of the stitches corresponding to the actual audio to serve

## configs/

See [https://github.com/kristopolous/DRR/wiki/Join-the-Federation](Joining the Federation) for an overview
of what these options are. Also, if you aren't faint of heart, you can look at the definition of the `defaults`
dict inside the `read_config()` function in [the main source](https://github.com/kristopolous/DRR/blob/master/server/indy_server.py) for
an overview of some of the more obscure parameters supported.

Inside the configs directory are the current configuration files for all the supported stations.
You could do a pull request to add one, or [send an email](mailto:indycast@googlegroups.com) to [the mailing list](https://groups.google.com/d/forum/indycast).


## server_query.py

This tool, given a populated database, will query all the servers or just one based,
on a callsign.  Here's the current end points for a server

### heartbeat                 /heartbeat
Lists the uptime and version, this is to make sure that the servers are all running ok

### site_map                  /site-map
A list of the endpoints supported

### restart                   /restart
An automated remote way to restart a misbehaving server

### upgrade                   /upgrade
Pulls down the latest from git and then upgrades the process if needed

### stats                     /stats
Shows a fairly verbose json structure of all things related to the server

### stream                    /[weekday]/[start]/[duration]/[showname].xml
Registers an intent and splices audio files (really quickly) to form on-demand podcasts
available for download.  Returns an xml that should be cross-compatible with all software

### send_stream               /slices/[path]
Corresponds to a particular stream, this is just a download path.

Example:

      $ ./server_query.py -q heartbeat 
      ---------
      kxlu.indycast.net:8890
      {
        "uptime": 1559, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      kpcc.indycast.net:8930
      {
        "uptime": 1559, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      kdvs.indycast.net:9030
      {
        "uptime": 1557, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      wxyc.indycast.net:8930
      {
        "uptime": 1557, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      wcbn.indycast.net:8830
      {
        "uptime": 1553, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      wfmu.indycast.net:9110
      {
        "uptime": 1554, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      kzsu.indycast.net:9010
      {
        "uptime": 1549, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      kvrx.indycast.net:9170
      {
        "uptime": 1547, 
        "version": "v0.1-61-g8ea1212"
      }
      ---------
      kcrw.indycast.net:8990
      {
        "uptime": 442, 
        "version": "v0.1-61-g8ea1212"
      }


Or a specific station:

    ./server_query.py -q stats -c kpcc 
    ---------
    kpcc.indycast.net:8930
    {
      "config": {
        "archivedays": "30", 
        "callsign": "kpcc", 
        "cascadebuffer": 15, 
        "cascadetime": 900, 
        "cycletime": "7", 
        "expireafter": "45", 
        "lat": "33.955766", 
        "loglevel": "debug", 
        "long": "-118.397920", 
        "mode": "full", 
        "port": "8930", 
        "storage": "/home/chris/radio/kpcc/", 
        "stream": "http://live.scpr.org/kpcclive/"
      }, 
      "disk": 87750, 
      "intents": [
        [
          1, 
          "3660:60", 
          3660, 
          3720, 
          0, 
          "2015-07-09 05:09:46", 
          "2015-07-09 05:09:46"
        ], 
        [
          2, 
          "3240:60", 
          3240, 
          3300, 
          0, 
          "2015-07-09 07:42:18", 
          "2015-07-09 07:42:18"
        ], 
        ...
        [
          7, 
          "3540:60", 
          3540, 
          3600, 
          0, 
          "2015-07-09 07:58:24", 
          "2015-07-09 07:58:24"
        ]
      ], 
      "kv": [
        [
          1, 
          "runcount", 
          "22", 
          "2015-07-07 06:45:54"
        ], 
        [
          2, 
          "offset", 
          "-420", 
          "2015-07-07 06:45:54"
        ], 
        [
          3, 
          "uptime", 
          "186053", 
          "2015-07-07 06:45:54"
        ]
      ], 
      "streams": [
        {
          "duration_sec": 932.7542857142857, 
          "end_minute": 1440.5459047619047, 
          "name": "streams/kpcc-1436226354.mp3", 
          "start_date": "Mon, 06 Jul 2015 23:45:54 GMT", 
          "start_minute": 1425, 
          "week": 28
        }, 
        {
          "duration_sec": 949.1330612244898, 
          "end_minute": 1455.8188843537414, 
          "name": "streams/kpcc-1436227244.mp3", 
          "start_date": "Tue, 07 Jul 2015 00:00:44 GMT", 
          "start_minute": 1440, 
          "week": 28
        }, 
        {
          "duration_sec": 254.92897959183674, 
          "end_minute": 1459.2488163265307, 
          "name": "streams/kpcc-1436228149.mp3", 
          "start_date": "Tue, 07 Jul 2015 00:15:49 GMT", 
          "start_minute": 1455, 
          "week": 28
        }, 
        ...
        {
          "duration_sec": 765.8579591836735, 
          "end_minute": 4529.764299319728, 
          "name": "streams/kpcc-1436411866.mp3", 
          "start_date": "Thu, 09 Jul 2015 03:17:46 GMT", 
          "start_minute": 4517, 
          "week": 28
        }
      ], 
      "uptime": 1629, 
      "version": "v0.1-61-g8ea1212"
    }


