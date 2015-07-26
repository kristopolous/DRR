# Miscellaneous tools

 * audio_hopper.py - This is where most of the map and mp3 parsing testing happens.  
 * backup.sh - Queries each station for a gzipped SQLite3 dump of their current database, putting them in a dated directory
 * cleanup_cloud.sh - Cross-references the cloud and a station's database, removing files that aren't accounted for.
 * cloud.py - A way to query the MS azure cloud storage that's being used. [It's routinely used to calculate the projects' budget](https://github.com/kristopolous/DRR/wiki/Current-Architecture)
 * get_stream.sh - Gets a remote mp3 and puts it locally.
 * graph.py - Shows a visual representation of a stations' recording coverage (look at the top of the code for more details).
 * indycast.pub - The public key you should add to your server in the authorized_keys files if you want to be part of the federation.
 * server_query.py - Queries the server(s) for information (see below)

The tools ending in .py all have documentation using python's argparser.  All tools are internally documented in their code - along with providing descriptions of what they do and how to use them at the top of the file.

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


