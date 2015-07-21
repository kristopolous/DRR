# Installation

To run the server, you need the things listed in the [bootstrap](https://github.com/kristopolous/DRR/blob/master/bootstrap.sh) file ( don't worry, this is a very simple file )

Your OS of choice should have these in their own terms - remember this is intended to be run on a server somewhere.

# Overview

There's a few things of interest here:

  1. indy_server.py
  1. configs/

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
 * slices         - Sliced versions of stitched audio corresponding to the actual audio to serve

### Audio processing

I explained the novel approach to the processing of the mp3s in pure python, in this [reddit post](https://www.reddit.com/r/Python/comments/3ch1vn/show_rpython_indycast_mostly_written_in_python/csvs64l). Essentially an mp3 file is a block-based stream.  Each block has a header and a payload.  You can get ID3 which is meta-information or MP3 data. 

Since you are downloading essentially a remote file which won't be magically transcoded, you can treat it like a file.  That is to say that if I download it from two different places, it will of course have the exact same bytes.

So what I've done is I took the first few bytes of the mp3 payload and then I checked over the course of a few samples of 10 million data blocks, how many bytes I would need to look at before asymptotically there was really no benefit.  I then used this as an "audio signature".  Effectively, I need to look for 5 sequential blocks with identical audio signatures.

Then I can presume that that region is the overlap and use those to stitch the audio together.

This method comptletely avoids mp3 decoding entirely and so is actually blisteringly fast.  It can process audio streams in fractions of a second. 

Because of this, the audio gets processed before the xml is returned ... the delay due to this fast method of processing is fairly imperceptible.

## configs/

See [Joining the Federation](https://github.com/kristopolous/DRR/wiki/Join-the-Federation) for an overview
of what these options are. Also, if you aren't faint of heart, you can look at the definition of the `defaults`
dict inside the `read_config()` function in [the main source](https://github.com/kristopolous/DRR/blob/master/server/indy_server.py) for
an overview of some of the more obscure parameters supported.

Inside the configs directory are the current configuration files for all the supported stations.
You could do a pull request to add one, or [send an email](mailto:indycast@googlegroups.com) to [the mailing list](https://groups.google.com/d/forum/indycast).


