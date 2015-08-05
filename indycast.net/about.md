# Introduction

Indycast is a set of federated servers controlled by a community for time-shifting independent radio.

I've been a listener and supporter of non-commercial radio for about 20 years.

In that time, I've found a few things:

 * Often the best shows are on at inconvenient hours
 * These shows are rarely archived
 * When the shows are archived, they have the following properties
    * I often need itunes, which I don't have
    * They break the show down into small units that must be reconstituted manually
    * You have to know every show and stations individual site
    * The retention policy of the audio and when it is availabe widely varies

However, they all have internet streams that you can listen to wherever.

### Version 1: circa 2010

So a few years ago I made a shell-scripted solution for this.  cron would fire off a downloader at the time my show was on, the downloader would time-stamp the web stream and dump it in a directory and then I can listen to it later.

This worked fine. For years actually.  But it was so useful I wanted to share this with everyone.

So I had to make a system that everyone could use.

## Designing something for everyone

I made a few decisions to set up the framework of the system early on:

 * **Non-commercial:**  I wanted a way to support and provide listener supported radio in a convenient manner
 * **Free:** Although I'm just building a platform, it didn't feel right charging people for this so it had to be free
 * **Distributed:** The architecture has to allow people from other places with their own stations to join the network without much effort
 * **Hackable:** Every device and reasonable way of listening to content should be supported

## Architecture

Since there's no money behind this, that means that I'd need a way to do this cheaply and in a way that has a really low barrier to entry
for participation.  I want to encourage people to run and manage their own servers for their favorite radio station.  

Here were my priorities, the solution should be:

 * easy and quick to setup.
 * a small-footprint, unobtrusive system that can piggy-back on servers doing other things.
 * highly configurable with reasonable defaults.
 * able to be disk and network effecient.
 * able to be run multiple times on the same machine for different stations.

It also should not

 * require significant dependencies
 * be language-specific with arcane knowledge needed in order to get it running.

So the stack chosen was Python 2.7, Flask, and SQLite 3. The audio library was written by hand.

## User-experience

### Administrator
I envisioned the ideal user-experience of someone who wants to participate in this:

#### Easy set-up
Alice, a junior dev, is interested in adding her station, RDIO.  She 

 * git clones the repository
 * runs a small shell script to install dependencies
 * goes to RDIO's website and finds the live stream url
 * puts the url in a configuration file, say rdio.txt
 * runs the server with this configuration file.

#### Self-contained

When the server starts up, it 

 * puts everything in a single directory with a simple to understand hierarchy
 * forks processes from a manager thread, carefully naming them with their purpose
 * has an informative log file that tells the user what's going on
 * is easy to shut down and restart
 * is remotely upgradable, replacing its own footprint seamlessly

#### Non-mysterious

There's an endpoint map so that the admin can see everything that is accessible along with its
documentation.  For instance

    $ curl indycast.net/kpcc/site-map
    /heartbeat      
        A low resource version of the /stats call ... this is invoked
        by the server health check.  Only the uptime of the server is reported.
        
        This allows us to check if a restart happened between invocations.
        

    /site-map        
        Shows all the end points supported by the current server, the options 
        and the documentation.
        

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


These can be queried using a server query tool, located in `tools/server_query.py`.  It can query any endpoint on any 
number of stations and parse JSON if desired.  For instance, if I wanted to see how much disk space kpcc is using I can do the following:

    $ tools/server_query.py -k disk -c kpcc
    {"url": "kpcc.indycast.net:8930", "latency": 2.824465036392212, "disk": 2000112}

Or, what if I wanted to find out the uptime and disk space of kpcc and kxlu?

    $ tools/server_query.py -k disk,uptime -c kpcc,kxlu
    [
    {"url": "kxlu.indycast.net:8890", "latency": 3.542130947113037, "uptime": 5235, "disk": 2283312},
    {"url": "kpcc.indycast.net:8930", "latency": 2.451361894607544, "uptime": 5250, "disk": 2000112}
    ]

As you can see, the server query presents this in a JSON array for our convenience.

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


### User
The user of the service should be able to use the service in any reasonable way with any reasonable set of expectations.

#### Subscribe to any time slot 
This should be accessible with a simple url schema:

    http://indycast.net/[station]/[weekday,...]/[start time]/[duration]/[name]

For instance, if there's a 2 hour show called, say "Darkwaves" at 2AM monday and wednesday mornings, you could do:
  
    http://indycast.net/rdio/mon,wed/2am/2hr/Darkwaves.xml

And that url should be openable in anything that ostensibly accepts "podcasts".

#### Listen to live radio with a delay
Alice turns on her radio and there's a fascinating interview going on.  Unfortunately, she missed the beginning of it.  She should
be able to listen to RDIO starting say, 5 minutes ago, by doing the following:

    http://indycast.net/rdio/live/-5min

Or, if she wanted to listen starting at 1pm, this should work:
    
    http://indycast.net/rdio/live/1pm

#### Pick any arbitrary time slice
If Alice just wants to listen to say, the Darkwaves show directly, from the command line, without all the hassle, she should be able
to specify a date, time, and duration, such as this:

    $ mplayer http://indycast.net/rdio/at/monday_2am/2hr

#### Should be usable by novices
If Alice doesn't really know how to use computers that well, there should be a [web front end](http://indycast.net) that explains what this is and 
has a simple and attractive user-interface that she can operate on the device of her choosing.
