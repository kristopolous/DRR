<div id='title'>
<div id='logo'><img src=images/square-indycast_70.png></div><div id='header'>
<h1>Indycast</h1><h3>A Distributed [Open Source](https://github.com/kristopolous/DRR) DVR for Independent Radio</h3></div>
</div>

## What is this?

Indycast is a set of [community-run servers](https://github.com/kristopolous/DRR/wiki/Current-Architecture) for time-shifting independent radio because

 * Often the best shows are on at inconvenient hours
 * Shows are rarely archived
 * When shows are archived, they often have the following properties
    * A proprietary solution such as iTunes is required.
    * They are broken into small units that must be reconstituted manually.
    * Every show and station has a different website with a different layout.
    * The retention policy of the audio and when it is availabe widely varies.

Essentially the existing landscape is laborious to use, inconsistent, technically restricted, and very incomplete in coverage.

Let's make things suck less. I'd like that, wouldn't you?

## Making things easy and powerful

The project's objectives:

 * **Free:** Build a community instead of looking to make a buck.
 * **Distributed:** People from other places can join the network using their stations without much effort.
 * **Hackable:** Every device and reasonable way of listening to content is supported.
 * **Non-commercial:** A way to provide listener-supported radio in a convenient manner.

## Modest goals for friendly software

There's no money behind this and it's designed to be cheap with a low barrier to entry for participation.  People are encouraged to run and manage their own servers for their favorite radio station.  Special care has been taken to make the software:

 * **Simple**: Easy and quick to setup - I've timed multiple people who have been asked to get it up and running.
 * **Small**: A small-footprint, unobtrusive system that can piggy-back on servers doing other things.
 * **Customizable**: Highly configurable with reasonable defaults.
 * **Efficient**: Able to be use minimal disk and network resources - extensive monitoring has been done.
 * **Self-contained**: Able to be run multiple times on the same machine for different stations - this is what is done in production.

The stack is Python 2.7 and SQLite 3. The audio library is written by hand (more below on why)

<img id='arch' style='max-width:92%' src=images/indy-arch.png>

## Focus on all the users

### Smooth and painless administration

Unlike with other projects, a minimal configuration to get a server up and running can be done in **[just 6 lines](https://github.com/kristopolous/DRR/blob/master/server/configs/kxlu.txt)**! 
There are [14 example configurations](https://github.com/kristopolous/DRR/tree/master/server/configs) which are about 7 lines each. These are the ones that are used in production. No kidding.

There's a bash script to install dependencies but again, [it's 12 lines](https://github.com/kristopolous/DRR/blob/master/bootstrap.sh) ... so if it doesn't work on your system, just `cat bootstrap.sh` and install the stuff yourself.  composer, gemfile, vundle, bower, something else? No! none of that - let's not re-invent things that are already easy.

Don't you hate it when some blackbox frameworky magic doesn't work and you helplessly try to figure out what's the code and what's the framework ... geez, I hate that.  No, none of that nonsense here.

In fact, I've created a user-story for a would-be administrator. Every interaction with a computer should be a thought-out interface.

#### Get a server up and running in under 2 minutes.
Alice is interested in adding her station, RDIO.  She 

 1. Git clones [https://github.com/kristopolous/DRR](https://github.com/kristopolous/DRR).
 1. Runs a [small shell script](https://github.com/kristopolous/DRR/blob/master/bootstrap.sh) `bootstrap.sh` to install dependencies: `cd DRR; ./bootstrap.sh`
 1. Goes to RDIO's website and finds the live stream url. <sup>1</sup>
 1. Puts the URL in a configuration file, say `server/configs/rdio.txt`.
 1. Runs the server with this configuration file, `./indy_server.py -c configs/rdio.txt`.

<small>[1] or use one of the examples: `./indy_server.py -c configs/kpcc.txt`</small>

With a fresh install of a Linode VPS instance, I was able to get a server up and running in <a href=images/record.png>23.87 seconds</a>.

Here I am, with a bunch of terrible typos, getting it up and running ... this is definitely not a speed run:

<iframe src="https://www.youtube.com/embed/8ZnFI1ncFcQ" frameborder="0" allowfullscreen></iframe>

#### Self-contained and hassle free

When the server starts up, it 

 * Puts everything in a single directory with a simple to understand hierarchy: `~/radio/rdio/` (configurable)
 * Forks processes from a manager thread, carefully naming them with their purpose.
 * Has an informative log file that tells the user what's going on: `~/radio/rdio/indycast.log`
 * Is easy to shut down and restart: `kill cat ~/radio/rdio/pid-manager`
 * Is remotely upgradable (through the `/upgrade` endpoint), replacing its own footprint seamlessly.

In fact if you run multiple stations you can see something like this:

    $ ls ~/radio
    kcrw  kdvs  kpcc  kxlu  wxyc
  
And if we dip into one of these, (notice how I'm not root or using sudo or any of that nonsense?) we'll see something like this:

    $ cd kpcc; find . | grep -v mp3
    .
    ./config.db
    ./slices
    ./backups
    ./backups/kpcc-20150723-2012.gz
    ./indycast.log
    ./streams
   
No voodoo and nothing cryptic. You can engage as much or as little with the technology as you want: all the way from auto-pilot to manual transmission.

Refreshing huh?


#### A zero mystery policy 

There's an endpoint map so Alice can see everything that is accessible along with its
documentation. As of the writing of this document, it looks like so:

    $ curl indycast.net/kpcc/help
    -=#[ Welcome to indycast v0.9-Inkanyamba-75-g10234a0 API help ]#=-

    /heartbeat      
        A low resource version of the /stats call ... this is invoked
        by the server health check.  Only the uptime of the server is reported.
        
        This allows us to check if a restart happened between invocations.
        

    /reindex         
        Starts the prune process which cleans up and offloads audio files but also re-index 
        the database.

        This is useful in the cases where bugs have led to improper registration of the 
        streams and a busted building of the database.  It's fairly expensive in I/O costs 
        so this shouldn't be done as the default.
        

    /restart         
        Restarts an instance. This does so in a gapless non-overlapping way.
        

    /upgrade        
        Goes to the source directory, pulls down the latest from git
        and if the versions are different, the application restarts.
        

    /prune           
        Starts the prune sub-process which cleans up and offloads audio files 
        following the rules outlined in the configuration file (viewable with the stats call)
        

    /stats           
        Reports various statistical metrics on a particular server.  
        Use this with the graph.py tool to see station coverage.
        

    /help            
        Shows all the end points supported by the current server, the options 
        and the documentation.
        

    /uuid            
        Returns this server's uuid which is generated each time it is run.
        This is used to determine whether this is the official server or not.
        

    /db              
        Backs up the current sqlite3 db and sends a gzipped version of it as the response.
        

    /[weekday]/[start]/[duration_string]/[showname] 
        Returns a podcast xml file based on the weekday, start and duration.
        This is designed to be read by podcasting software such as podkicker, 
        itunes, and feedburner.

        weekdays are defined as mon, tue, wed, thu, fri, sat, sun.

        If a show occurs multiple times per week, this can be specified with
        a comma.  for instance,

        /mon,tue,fri/4pm/1hr
        
        The showname should be followed by an "xml" extension.

        It should also be viewable in a modern web browser.

        If you can find a podcaster that's not supported, please send an email 
        to indycast@googlegroups.com.
        

    /at/[start]/[duration_string] 
        Sends a stream using a human-readable (and human-writable) definition 
        at start time.  This uses the dateutils.parser library and so strings 
        such as "Monday 2pm" are accepted.

        Because the space, 0x20 is such a pain in HTTP, you can use "_", 
        "-" or "+" to signify it.  For instance,

            /at/monday_2pm/1hr

        Will work fine
        

    /[weekday]/[start]/[duration_string] 
        This is identical to the stream syntax, but instead it is similar to
        /at ... it uses the same notation but instead returns an audio file
        directly.

        You must specify a single weekday ... I know, total bummer.
        

    /slices/[path] 
        Downloads a stream from the server. The path is callsign-date_duration.mp3

          * callsign: The callsign returned by /stats
          * date: in the format YYYYMMDDHHMM such as 201508011005 for 
            2015-08-01 10:05
          * duration: A value, in minutes, to return.

        The mp3 extension should be used regardless of the actual format of the stream -
        although the audio returned will be in the streams' native format.
        
        The streams are created and sent on-demand, so there may be a slight delay before
        it starts.
        

    /live/[start]  
        Sends off a live-stream equivalent.  Two formats are supported:

         * duration - In the form of strings such as "1pm" or "2:30pm"
         * offset - starting with a negative "-", this means "from the present".
            For instance, to start the stream from 5 minutes ago, you can do "-5"

        

##### Bulk Queries with JSON output

These endpoints can be conveniently queried in bulk using a server query tool, located in `tools/server_query.py`.  

It can query any endpoint on any number of stations and parse JSON if desired.  For instance, if I wanted to see how much disk space kpcc is using I can do the following:

    $ tools/server_query.py -k disk -c kpcc
    {"url": "kpcc.indycast.net:8930", "latency": 2.824465036392212, "disk": 2000112}

Or, if I wanted to find out the uptime and disk space of kpcc and kxlu:

    $ tools/server_query.py -k disk,uptime -c kpcc,kxlu
    [
    {"url": "kxlu.indycast.net:8890", "latency": 3.542130947113037, "uptime": 5235, "disk": 2283312},
    {"url": "kpcc.indycast.net:8930", "latency": 2.451361894607544, "uptime": 5250, "disk": 2000112}
    ]

The server query presents the output as valid JSON to do with it whatever you please.

##### Graphical comprehension 

If you'd like to find out what the station coverage is, there's a graph-drawing tool that tells you.

    $ tools/server_query.py -q stats -c kpcc | tools/graph.py 

             +-0---1---2---3---4---5---6---7---8---9---10--11--12--13--14--15--16--17--18--19--20--21--22--23--+
    2015-07-06 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . |
    2015-07-07 *=******.*********************************************.**************************************** |
    2015-07-08 ************************************************* **********************************************|
    2015-07-09 .***********************************.********************************************************** |
    2015-07-10 ******************************************************* *******=******************************* |
    2015-07-11 **************.**************** .*********************************.**************************** |
    2015-07-12 ***************** *********************************************************************** ******|
    2015-07-13 .********************** ***********************************=****************.*******************|
    2015-07-14 .***************.*****************.******** ****************************************************|
    2015-07-15 .***********************************************************************************************|
    2015-07-16 . *********=********************=*******************=**********************************=********|
    2015-07-17 .************** ***** ********************************************************* ******* ******* |
    2015-07-18 *********************************************** ****************. . . . . . . . . . .***********|
    2015-07-19 .***********************************************************************************************|
    2015-07-20 .***********************************************************************************************|
    2015-07-21 .***********************************************************************************************|
    2015-07-22 .***********************.***********************************************.********************** |
    2015-07-23 .****************************************************************============*************.** **|
    2015-07-24 ************************************************************************====. . . . . . . ******|
    2015-07-25 .***.**** ***************************** *************** .******************** ************.*****|
    2015-07-26 .*********************************************************************.************ ********.***|
    2015-07-27 .****==== ******************************* **********************.*********.*************.*******|
    2015-07-28 .****** *************************** *********************** *********************************** |
    2015-07-29 ***************************************************======*************===************ ********* |
    2015-07-30 ************* ******************************=========*******.****** .*.************************ |
    2015-07-31 .************************************************** ******************.************************ |
    2015-08-01 *********************************************************************************************=* |
    2015-08-02 **=*************************==************* .**** ********************************************* |
    2015-08-03 *** ***** *********************************** ********* ******.** *** *******=======*********** |
    2015-08-04 ********.**************************************************** . . . . . . . . . . . . . . . . . |
             +-0---1---2---3---4---5---6---7---8---9---10--11--12--13--14--15--16--17--18--19--20--21--22--23--+

             kpcc coverage: 90.877315%


### Being a Consumer
The consumer the service should be able to use the service in any reasonable way with any reasonable set of expectations.

#### Easy for novices
If Alice doesn't really know how to use computers that well, there is a [web front end](http://indycast.net) that explains what indycast is and has a simple and attractive user-interface that she can operate on the device of her choosing.

There's [three cognitively distinct](https://github.com/kristopolous/DRR/issues/104) ways to think about indycast:

 * **Podcaster**: A service where you specify time slices to use (I have 4 that I use)
 * **DVR**: You can start live radio in the past and then pause and scrub it.
 * **Concierge**: Set an email reminder to listen to a show later.

##### What's a Concierge?

The Concierge service is the only one that ought to need explanation.  Assume Alice is listening to a wonderful lecture, let's say [Intellectual Ecology: Green Chemistry and Biomimicry](http://media.bioneers.org/listing/intellectual-ecology-green-chemistry-and-biomimicry-john-warner/) but it's on at an inconvenient time and she has things to do with her life.

She can [set a reminder](http://indycast.net/reminder) which uses `localStorage` to remember her email address and the last station 
she selected.

There she has a convenient selection of specifying the current half hour, 1-hour, or 2-hour time slot.  Then she can specify a note such as "John Warner's subversive ideas on chemistry".  And then, at some time later, an email gets sent back to her saying "Hey here's the audio you requested with the notes your specified.  Here's a download link".

In that way, it's a radio concierge service, looking out for you.

##### Convenient for all levels of interaction

Not only was this technology designed to be used by people who thumb around their smart-phones, but it was also designed for people who
do Tux-cosplay at Linux conferences and think DefCon is full of posers.  

If you are a hacker, read on.  Alice is a hacker.  She has no problem using a command line. 

## Makes hackers do the splits while shooting <a href=http://i.dailymail.co.uk/i/pix/2014/12/21/24333D7D00000578-0-image-m-13_1419157979609.jpg>party poppers</a>

The first thing that Alice does is `curl` the main indycast site.  

Normally this is a stupid idea as she would get a bunch of terribly formatted server-generated HTML, but not with indycast!  Here is what she sees:

    $ curl http://indycast.net/    
    The current stations are healthy:

     * http://indycast.net/kcrw/
     * http://indycast.net/kdvs/
     * http://indycast.net/kpcc/
     * http://indycast.net/kpfk/
     * http://indycast.net/kspc/
     * http://indycast.net/kusf/
     * http://indycast.net/kvrx/
     * http://indycast.net/kxlu/
     * http://indycast.net/kzsu/
     * http://indycast.net/wcbn/
     * http://indycast.net/wfmu/
     * http://indycast.net/wxyc/
     * http://indycast.net/wzrd/

    Query the /site-map end-point to see
    supported features on a per-station basis.

    Thanks for using curl/7.26.0 ;-).
    $

Finally someone cares about the hackers.  She can easily copy and paste the stubs to access the API.

#### Subscribe to any show

XMLs podcasts feed are generated with a simple url schema:

    http://indycast.net/[station]/[weekday,...]/[start time]/[duration]/[name]

Let's say there's a 2 hour show called, say *Darkwaves* at 2AM Monday and Wednesday mornings, you could do:
  
    http://indycast.net/rdio/mon,wed/2am/2hr/Darkwaves.xml

That URL would happily works with anything that ostensibly accepts so-called *podcasts*.

Or if you prefer, since the XML gets printed in a human readable pretty-print format, we can just cut the BS and do something like this:

    $ curl -s kxlu.indycast.net:8890/sun/7pm/1hr/show.xml | grep enclosure 
      <enclosure url="http://kxlu.indycast.net:8890/slices/kxlu-201507261900_62.mp3" length="59520000" type="audio/mpeg"/>
      <enclosure url="http://kxlu.indycast.net:8890/slices/kxlu-201508021900_62.mp3" length="59520000" type="audio/mpeg"/>
    $

Like a boss. Alice is a boss.  

BTW, the audio intentionally starts a bit early and goes a bit over because in the real world, shows don't end on some exact NTP millisecond.

### Rewind, pause, and scrub live radio
Alice turns on her radio and there's a fascinating interview going on.  Unfortunately, she missed the beginning of it.  Luckily, she is able to listen to RDIO starting say, 5 minutes ago, by doing the following:

    $ mplayer http://indycast.net/rdio/live/-5min

Or, if she wants to listen starting at 1pm, this works:
    
    $ mpg321 http://indycast.net/rdio/live/1pm


#### Listen to user-specified arbitrary time slices
If Alice just wants to listen to say, the Darkwaves show directly, from the command line, without all the hassle, she can specify a date, time, and duration, such as this:

    $ mplayer2 http://indycast.net/rdio/at/monday_2am/2hr

In fact, there's another more orthogonal way to do this, for Bob, who is forgetful and lazy:

    $ mpv http://indycast.net/rdio/mon/2am/2hr

See how this is similar to the podcast link of 

    http://indycast.net/rdio/mon/2am/2hr/Darkwaves.xml

Simply by omitting the christening of the show and stopping after the duration, the server figures you just want the most recent 
episode and gives it to you.  How nice for Bob.


## Fast and small

### Disk space efficient

VPSs generally don't give that much disk space and archiving audio would normally take a lot of it.

There's two systems here. You can put your server in [on-demand mode](https://github.com/kristopolous/DRR/wiki/Join-the-Federation), which means that lots of things can't be done (basically, just forward-moving subscriptions), or you can use cloud storage.

A survey was done in July 2015 to try to find the cheapest storage options:

  * Amazon EC2: $0.050 / GB
  * Google Compute: $0.040 / GB
  * Microsoft Azure: $0.024 / GB

Coming in at less than half the price of EC2, MS Azure was the obvious choice.  If configured with
credentials, the server will use an Azure account to offload the valuable disk space on the VPS. If you would rather use another service, [open a bug](https://github.com/kristopolous/DRR/issues).

A tool `tools/cloud.py` computes the current cost for the stations specified.  Also, a tool
`tools/cleanup_cloud.sh` will analyze all the content on the cloud and make sure that it's valid
and in use by looking at a recent backup and doing a station-by-station comparison. Here is an example:

    $ tools/cloud.py

     Station   Files   Space (GB)
    -----------------------------
    14: kcrw   1738    22.467
    13: kdvs   1938    25.881
    12: kpcc   2792    18.477
    11: kpfk   5000     4.069
    10: krvm    341     3.470
     9: kspc   1508    20.169
     8: kusf    865    11.661
     7: kvrx   2693    54.312
     6: kxlu   2661    35.260
     5: kzsu   4273    35.511
     4: wcbn   2681    34.591
     3: wfmu   1717    23.250
     2: wxyc   1114    14.798
     1: wzrd   1038     3.368
    -----------------------------
     Total    30359   307.282 GB
     Cost     $7.37/month

     *using $0.024/GB azure pricing



### CPU efficient

There is **no audio processing done** on the server.  No ffmpeg, avconv, lame, mencoder.  No
none of that.  It can all be cleverly avoided - lemee 'splain:

Because audio streams are just binary files, and the binary files are identical 
independent of the user downloading them, then in order to overlap or splice the audio 
all you need is the ability to parse and find the headers ... not the payloads themselves.

In order to find matching payloads, you can look at a sequence of bytes, called a signature, at
the beginning of the payloads, and simply match that.  No audio-fingerprinting or FFT between 
time and frequenc... no none of that.  It's much faster.

But since there was no library out there that did just this, I had to roll my own (see [server/lib/audio.py](https://github.com/kristopolous/DRR/blob/master/server/lib/audio.py)).  It scans headers, hopping around the file, making a number of 
bold assumptions about things (such as CBR encoding) and as a result, audio can be brought down 
from the cloud storage, stitched together, and then sliced in under a second.

The audio processing engine wasn't designed to process all MP3 and AAC files ... in fact, it was designed 
to deal with broken headers, files that are cut off, that begin in the middle of a payload, etc.

Bitrates in fact, are computed based on the rate of the bits transiting over the connection in a given duration as opposed
to being internally taken from what the file says it is.  

This is a much more direct and format agnostic computation.  The sample size is large enough to avoid any 
errors (in fact, for HE-AAC+ streams, it performs more accurate duration measurements then `ffprobe` ... really).

### Offloaded dependencies

When things would take too many dependencies, the task was intentionally off-loaded to the main website in order to
minimize the complexity and responsibilities behind running a server.  The server has a distinct and unique purpose in life.

But that doesn't stop us from our fun hacking.

#### Restful logo generation

Logos for the podcasts are generated server-side at indycast.net so as not to require any image-processing
or font dependencies on the servers themselves.  The background tint is chosen based on the word 
itself in order to create a diverse but distinct palette for the various logos. 

The schema for generating them looks like the following

    http://indycast.net/icon/(Arbitrary_string)_(size).png

For instance:

    <img src=http://indycast.net/icon/Here+is+one_120.png>
    <img src=http://indycast.net/icon/And+here+is+another_120.png>
    <img src=http://indycast.net/icon/You+can+go+small_90.png>

Looks like so:

<div id='logo-block'>
<img src=http://indycast.net/icon/Here+is+one_120.png><img src=http://indycast.net/icon/And+here+is+another_120.png><img src=http://indycast.net/icon/You+can+go+small_90.png>
</div>

The logos are 16-color PNGs which make them small and fast (although admittedly kind of ugly).

#### Is this legal?

*I have no idea; I'm not a lawyer*. We're solving real-world problems here so let's see what happens. This technology
has been a total game-changer in the way I listen to radio. Really.

If you're really concerned, then go ahead and run your own network of servers for personal private use - you
can easily stuff 25 stations on any half-assed modern consumer-grade internet connection. Each instance takes 
up about 80MB of resident memory so we are still just talking 2GB for all that.

## Have the goals been met?

In writing this software I wanted to have something that worked and follows principles in usability, transparency,
adaptability, and simplicity that are held dearly by me.  I've tried to create this in the way that I want software
to be written.

Given that, I hope you enjoyed reading this and use indycast.  I've been working full-time, 7 days a week on it since
June 2015 and encourage you to become part of the community.  

If there are stations you'd like to support, or better yet, money you'd like to donate, [a wiki has been set up](https://github.com/kristopolous/DRR/wiki) 
describing:

 * How to run your own server
 * The current cost and server architecture
  
I also encourage you to [pull down the code](https://github.com/kristopolous/DRR) which I have taken a serious
effort on to be consistent and well-documented.  If you find issues, please feel free to send a pull-request.

Thanks for reading.

~chris.

