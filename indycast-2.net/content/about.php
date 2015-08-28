  <style>
  body { 
    background: url('images/crossword.png'); }
  p {
    margin-left: 10px;
    max-width: 700px;
    line-height: 1.4em;
  }
  iframe {
    width: 420px;
    height: 315px;
  }
  em {
   font-family: 'Slabo 27px', serif;
   font-size: 1.05em;
  }
  #logo {
    float: left;
    margin-left: 10px;
    width: 70px;
    height: 90px;
  }
  #header {
    margin-left: 95px;
    min-height: 90px;
  }
  #header h1 {
    padding-top: 5px;
  }
  #title { 
    margin-top: 20px;
  }
  #logo-block { margin-left: 30px; }
  img {
    border: 1px solid rgba(128,128,128,0.5);
    margin: 2px;
    padding: 2px;
  }
  #header * { 
    margin: 0;
  }
  h1,h2,h3,h4,h5,h6 {
    color: #002244;
    line-height: 1.5em;
  }
  h2 { margin-left: 10px; }
  h3 { margin-left: 20px; margin-top: 30px; }
  h5,h4 { margin-left: 40px; margin-top: 30px; }
  h5 { 
    padding-bottom: 0.75em;
    max-width: 740px;
    border-bottom: 1px solid rgba(0,34,68,0.2);
  }
  
  #header h3 {
    line-height: 1.1em;
  }
  h2 ~ p, h2 ~ iframe, { margin-left: 20px; }
  h3 ~ table, h3 ~ iframe, h3 ~ p, h3 ~ ul, h3 ~ ol, h3 ~ pre { margin-left: 40px; }
  
  th, td {
    padding-right: 12px;
  }
  li {
    line-height: 1.3em
  }
  code, pre{
    font-family: 'Inconsolata', monospace;
  }
  pre {
    display: inline-block;
    line-height: 1.25em;
    width: auto;
    background: #f8fafd;
    box-shadow: 0 0 2px 0px #ddd inset;
    padding: 0.5em 12px;
    border-radius: 5px;
    margin: 0 1em;
    max-height: 32em;
    overflow-y: auto;
    overflow-x: hidden;
  }
  code {
    text-shadow: 0px 0px 1px #aaa;
  }
  pre > code {
    font-size: 0.9em;
    color: #131;
    text-shadow: 0 0;
  }
  blockquote small {
    margin-top: 0.25em;
    display: block;
    color: #667;
    line-height: 1.2em;
    font-size: 0.7em;
  }
  blockquote {
    border-top: 4px solid #eef;
    border-bottom: 4px solid #eef;
    font-size: 1.25em;
    color: #334;
    width: 30%;
    float: right;
    padding: 0.5em 1em;
    background: rgba(216,216,255, 0.1);
    margin: 0.1em 0.2em 0.1em 0.4em;
  }
  blockquote p {
    line-height: 1.15em;
    margin: 0;
  }
  #radio-random { 
    margin-left: 10px;
    background: black;
    border-radius: 4px;
    padding: 0.5em;
    display: inline-block;
    color: white;
    font-family: sans-serif; 
  }
  #radio-random h2 {
    margin: 0;
    padding: 0;
    font-weight: normal;
    display: inline-block;
    font-size: 20px;
    color: white;
    font-family: sans-serif;
  }
  #radio-random audio {
    display: block;
    width: 100%;
  }
  #flash-widget {
    height: 30px;
  }
  #radio-widget {
    margin-top: 0.5em;
    height: 30px;
  }
  #button-random {
    background: black;
    color: white;
    border: 1px solid #aaa;
    border-radius: 3px;
    font-size: 14px;
    margin-right: 0.5em;
    vertical-align: text-bottom;
  }
  
  @media screen and (max-width: 1280px) {
    blockquote { font-size: 0.90em }
    body{ background: white }
    iframe {
      width: 95%;
      max-width: 420px;
    }
    pre, code {
      max-width: 85%;
      overflow-x: auto;
      font-size: 1em;
      margin-right: 0;
    }
    #radio-random { 
      margin-left: 6px;
    }
    #radio-random h2 {
      font-size: 15px;
    }
    li, p { line-height: 1.45em }
    p, h2 { margin-left: 3px; }
    h3 { margin-left: 6px; }
    #logo-block, h4 { margin-left: 9px; }
    
    h2 ~ p, h2 ~ iframe { margin-left: 6px; }
    h3 ~ table, h3 ~ p, h3 ~ ul, h3 ~ ol, h3 ~ pre, h5 { margin-left: 12px; }
    ul ul { margin-left: 0px;  padding-left: 1em }
    ul ul li {padding-left: 0px }
    #logo, #header { min-height: 120px; }
  }
  </style>
<div id="title">
<div id="logo">
<a href="/"><img src=/images/square-indycast_70.png></a>
</div>
<div id="header">
<h1>
<a href="/">Indycast</a>
</h1>
<h3>
A Distributed <a href="https://github.com/kristopolous/DRR">Open Source</a> DVR for Independent Radio
</h3>
</div>
</div>
<h2 id="a-free-open-source-service">A free open-source service</h2>
<p>Indycast is a set of <a href="https://github.com/kristopolous/DRR/wiki/Current-Architecture">community-run servers</a> for time-shifting independent radio because</p>
<ul>
<li>Often the best shows are on at inconvenient hours</li>
<li>Shows are rarely archived</li>
<li>When shows are archived, they often have the following properties
<ul>
<li>A proprietary solution such as iTunes is required.</li>
<li>They are broken into small units that must be reconstituted manually.</li>
<li>Every show and station has a different website and can be hard to navigate.</li>
<li>The retention policy of the audio and when it is availabe widely varies.</li>
</ul></li>
</ul>
<p>The existing landscape is laborious to use, inconsistent, technically restricted, and very incomplete in coverage.</p>
<p>Let's make things suck less.</p>
<h2 id="demo-time">Demo Time!</h2>
<p>Here's a random URL generator that allows you to see <code>/live</code> endpoints on healthy stations ... in more sophisticated audio players you could scrub up to the current time. Click on the button to the left of the URL to go to a new station and time</p>
<div id="radio-random">
<button id="button-random" onclick="do_random()">
↻
</button>
<h2 id="url">
</h2>
<div id='radio-widget'>
<div id='html5-widget'>
<audio id="radio-control" controls type='audio/mpeg'>
</div>
<div id="flash-widget">

</div>
</div>
</div>
<p>There's much more where that came from - weekly podcasts, email reminders, m3u, pls files, and more. Read on!</p>
<h2 id="easy-extendable-transparent-and-powerful">Easy, extendable, transparent, and powerful</h2>
<p>All the code, APIs, and services are:</p>
<ul>
<li><strong>Free:</strong> Community, not commercially driven.</li>
<li><strong>Distributed:</strong> People from other places can join the network using their stations with little effort.</li>
<li><strong>Hackable:</strong> Every device and reasonable way of listening to content is supported.</li>
<li><strong>Non-commercial:</strong> A way to provide listener-supported radio in a convenient manner.</li>
</ul>
<h2 id="modest-goals-for-friendly-software">Modest goals for friendly software</h2>
<p>The server architecture is carefully designed to be cheap to operate with low barriers to entry. <a href="https://github.com/kristopolous/DRR/wiki/Join-the-Federation">You are encouraged</a> to run and manage your own servers for your favorite radio station. Special care has been taken to make the software:</p>
<blockquote>
<p><em>Natural</em> products feel like they've always existed - it's hard to remember life before them.</p>
</blockquote>
<ul>
<li><strong>Simple</strong>: Easy and quick to setup - I've timed multiple people who have been asked to get it up and running.</li>
<li><strong>Small</strong>: A small-footprint, unobtrusive system that can piggy-back on servers doing other things.</li>
<li><strong>Customizable</strong>: Highly configurable with reasonable defaults.</li>
<li><strong>Efficient</strong>: Able to be use minimal disk and network resources - extensive monitoring has been done.</li>
<li><strong>Self-contained</strong>: Able to be run multiple times on the same machine for different stations - this is what is done in production.</li>
</ul>
<p>You can make a significant and meaningful contribution to this project cheap and effortlessly.</p>
<p>The stack is Python 2.7 and SQLite 3. The audio library is written by hand (more below on why)</p>
<p>Here's a run-down of everything, in picture format:</p>
<p><img id='arch' style='max-width:95%' src=images/indy-arch.png></p>
<h3 id="there-is-no-app.-repeat-there-is-no-app.">There is no app. Repeat: there is no app.</h3>
<p>This has been one of the hardest sales to people. This is intentionally designed to fit within the out-of-the-box capabilities of most consumer hardware. Explaining this to people has been an uphill battle.</p>
<p>People have become accustomed to having to download the app, register for the service, click on a confirmation email ... but this is just a website that works with your device; there should be no perceived risk.</p>
<p>However, giving access to minute-addressable streams of radio over any device through minimalistic url schemes just seems to flutter away like some kind of gibberish. The system works though, there's dozens of users I've pitched in person, by hand (and growing daily).</p>
<h2 id="focus-on-all-the-users">Focus on all the users</h2>
<h3 id="smooth-and-painless-administration">Smooth and painless administration</h3>
<p>Unlike with other projects, a minimal configuration to get a server up and running can be done in <strong><a href="https://github.com/kristopolous/DRR/blob/master/server/configs/kxlu.txt">just 6 lines</a></strong>! There are <a href="https://github.com/kristopolous/DRR/tree/master/server/configs">16 example configurations</a> which are about 7 lines each. These are the ones that are used in production. No kidding.</p>
<p>There's a bash script to install dependencies but again, <a href="https://github.com/kristopolous/DRR/blob/master/bootstrap.sh">it's 12 lines</a> ... so if it doesn't work on your system, just <code>cat bootstrap.sh</code> and install the stuff yourself. composer, gemfile, vundle, bower, something else? No! none of that - let's not re-invent things that are already easy.</p>
<blockquote>
<p>The record for upping a server from a fresh install is in <a href=images/record.png>23.87 seconds</a>.</p>
</blockquote>
<p>Don't you hate it when some blackbox frameworky magic doesn't work and you helplessly try to figure out what's the code and what's the framework ... No, none of that nonsense here.</p>
<!--Take omnibus-gitlab for instance.  It requires runit, redis, chef, postgres, nginx, ruby, unicorn, sidekiq, rails, logrotate, installs over 100,000 files into the /opt directory, takes up 3GB of disk (before doing anything) and eats up about 800MB of memory.  Even after you "uninstall" it, it still leaves behind 1.1GB of files just for the memories.  

Their tagline should be *Gitlab: The most elaborate and sophisticated way to store and view categorized blobs of text - A perverse exercise in absurdist art*.  You're supposed to look and think "Ah yes, a fancifully exagerrated work commenting on a race to the obtuse which has characterized the zeitgeist of modern programming - very well done".  But lo! They are serious. /me vigorously fans some flames

Let's build some contrast. indycast:

 * doesn't come with its own init system that nobody knows how to use.
 * doesn't fire up an SQL server, nosql store, or cache layer.
 * doesn't need a sandbox because indycast plays nicely with others - as a responsible citizen in the community known as a Linux system.
-->
<p>Really, this won't be an episode of <em>Programmers Gone Wild!</em> Are you in?</p>
<p>Good.</p>
<p>I've created a user-story for a would-be administrator because every interaction with a computer should be a thought-out interface.</p>
<h2 id="up-and-running-in-under-2-minutes.">Up and running in under 2 minutes.</h2>
<p>Try this out right now. It's easy and there's no risk.</p>
<p><a href=http://i.imgur.com/YI3Qu5bl.jpg>Alice</a> is interested in adding her favorite station, KPCC. She</p>
<ol style="list-style-type: decimal">
<li>Git clones <a href="https://github.com/kristopolous/DRR" class="uri">https://github.com/kristopolous/DRR</a>.</li>
<li>Runs a <a href="https://github.com/kristopolous/DRR/blob/master/bootstrap.sh">small shell script</a> <code>bootstrap.sh</code> to install dependencies: <code>cd DRR; ./bootstrap.sh</code></li>
<li>Runs the server with one of the example configuration files, <code>./indy_server.py -c configs/kpcc.txt</code>.</li>
</ol>
<p>Here with a bunch of terrible typos, getting it up and running ... this is definitely not a speed run:</p>
<iframe src="https://www.youtube.com/embed/8ZnFI1ncFcQ" frameborder="0" allowfullscreen>
</iframe>
<h4 id="self-contained-and-hassle-free">Self-contained and hassle free</h4>
<p>When the server starts up, it</p>
<ul>
<li>Puts everything in a single directory with a simple to understand hierarchy: <code>~/radio/kpcc/</code> (configurable)</li>
<li>Forks processes from a manager thread, carefully naming them with their purpose.</li>
<li>Has an informative log file that tells the user what's going on: <code>~/radio/kpcc/indycast.log</code></li>
<li>Is easy to shut down and restart: <code>kill cat ~/radio/kpcc/pid-manager</code> or even <code>pkill callsign</code></li>
<li>Is remotely upgradable (through the <code>/upgrade</code> endpoint), replacing its own footprint seamlessly.</li>
</ul>
<p>In fact if you run multiple stations you can see something like this:</p>
<pre><code>$ ls ~/radio
kpfa  kpfk  kpcc </code></pre>
<p>In fact, if I look at the process tree of this machine I see this:</p>
<pre><code>$ ps af -o comm= | grep kp
 kpfa-manager
  \_ kpfa-webserver
  \_ kpfa-download
 kpfk-manager
  \_ kpfk-webserver
  \_ kpfk-download
 kpcc-manager
  \_ kpcc-webserver
  \_ kpcc-download

$ uptime
00:34:02 up 579 days, 18:04,  1 user,  load average: 0.01, 0.01, 0.01</code></pre>
<p>0.01 ... for 3 of them</p>
<p>If we dip into one of these, (notice how I'm not root or using sudo or any of that nonsense?) we'll see something like this:</p>
<pre><code>$ cd kpcc; find . | grep -v mp3
.
./config.db
./slices
./backups
./backups/kpcc-20150723-2012.gz
./indycast.log
./streams</code></pre>
<p>No voodoo and nothing cryptic. You can engage as much or as little with the technology as you want: all the way from auto-pilot to manual transmission.</p>
<p>Refreshing huh?</p>
<h4 id="a-zero-mystery-policy">A zero mystery policy</h4>
<p>Everything is laid bare for inspection, both statically, and while running in production. You can get the statistics or any information on the running servers. The APIs are public and self-documented.</p>
<p>This is to encourage a &quot;policy of least magic&quot; because when such tricks don't work, one must reverse-engineer trickery - thus it's better to avoid trickery.</p>
<h5 id="no-secret-backend">No secret backend</h5>
<blockquote>
<p>Systems are vastly improved by the act of making visible what was invisible before. <small>Donald Norman, <em>The Design of Everyday Things</em></small></p>
</blockquote>
<p>Usually with most other projects, there's a secret &quot;admin&quot; backend that you, lowly outer-party developer don't get to see. You need an account, and to know the secret handshake ... screw that.</p>
<p>With indycast, there is an admin interface, <a href="http://indycast.net/admin.php">and it's right here</a>. You need to know a password to edit it or reveal sensitive information of course --- but you are free to see <em>all the inner-workings</em> of the platform.</p>
<h5 id="whats-this-a-help-endpoint-ce-nest-pas-possible">What's this? A help endpoint? <em>Ce n'est pas possible!</em></h5>
<p>There's an endpoint map so Alice can see everything that is accessible along with its documentation. As of the writing of this document (v0.9-<a href="https://roadtravel1.files.wordpress.com/2013/09/inkanyamba-1.jpg">Inkanyamba</a>), the help looks like this:</p>
<pre><code>$ curl indycast.net/kpcc/help
-=#[ Welcome to indycast v0.9-Inkanyamba-75-g10234a0 API help ]#=-

/heartbeat      
    A low resource version of the /stats call ... this is invoked
    by the server health check.  Only the uptime of the server is reported.
    
    This allows us to check if a restart happened between invocations.
    

/reindex         
    Starts the prune process which cleans up and offloads audio files but also re-index 
    the database.

    This is useful in the cases where bugs have led to improper registration of the 
    streams and a busted building of the database.  It&#39;s fairly expensive in I/O costs 
    so this shouldn&#39;t be done as the default.
    

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
    Returns this server&#39;s uuid which is generated each time it is run.
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
    
    The showname should be followed by an &quot;xml&quot; extension.

    It should also be viewable in a modern web browser.

    If you can find a podcaster that&#39;s not supported, please send an email 
    to indycast@googlegroups.com.
    

/at/[start]/[duration_string] 
    Sends a stream using a human-readable (and human-writable) definition 
    at start time.  This uses the dateutils.parser library and so strings 
    such as &quot;Monday 2pm&quot; are accepted.

    Because the space, 0x20 is such a pain in HTTP, you can use &quot;_&quot;, 
    &quot;-&quot; or &quot;+&quot; to signify it.  For instance,

        /at/monday_2pm/1hr

    Will work fine
    

/[weekday]/[start]/[duration_string] 
    This is identical to the stream syntax, but instead it is similar to
    /at ... it uses the same notation but instead returns an audio file
    directly.

    You must specify a single weekday ... total bummer.
    

/slices/[path] 
    Downloads a stream from the server. The path is callsign-date_duration.mp3

      * callsign: The callsign returned by /stats
      * date: in the format YYYYMMDDHHMM such as 201508011005 for 
        2015-08-01 10:05
      * duration: A value, in minutes, to return.

    The mp3 extension should be used regardless of the actual format of the stream -
    although the audio returned will be in the streams&#39; native format.
    
    The streams are created and sent on-demand, so there may be a slight delay before
    it starts.
    

/live/[start]  
    Sends off a live-stream equivalent.  Two formats are supported:

     * duration - In the form of strings such as &quot;1pm&quot; or &quot;2:30pm&quot;
     * offset - starting with a negative &quot;-&quot;, this means &quot;from the present&quot;.
        For instance, to start the stream from 5 minutes ago, you can do &quot;-5&quot;</code></pre>
<h5 id="bulk-queries-with-json-output">Bulk Queries with JSON output</h5>
<p>These endpoints can be conveniently queried in bulk using a server query tool, located in <code>tools/server_query.py</code>.</p>
<p>It can query any endpoint on any number of stations and parse JSON if desired. For instance, if you wanted to see how much disk space kpcc is using you can do the following:</p>
<pre><code>$ tools/server_query.py -k disk -c kpcc
{&quot;url&quot;: &quot;kpcc.indycast.net:8930&quot;, &quot;latency&quot;: 2.824465036392212, &quot;disk&quot;: 2000112}</code></pre>
<p>Or, if you wanted to find out the uptime and disk space of kpcc and kxlu:</p>
<pre><code>$ tools/server_query.py -k disk,uptime -c kpcc,kxlu
[
{&quot;url&quot;: &quot;kxlu.indycast.net:8890&quot;, &quot;latency&quot;: 3.542130947113037, &quot;uptime&quot;: 5235, &quot;disk&quot;: 2283312},
{&quot;url&quot;: &quot;kpcc.indycast.net:8930&quot;, &quot;latency&quot;: 2.451361894607544, &quot;uptime&quot;: 5250, &quot;disk&quot;: 2000112}
]</code></pre>
<p>The server query presents the output as valid JSON to do with it whatever you please. No more &quot;easy things hard and everything else impossible&quot;.</p>
<h5 id="graphical-comprehension">Graphical comprehension</h5>
<p>If you'd like to find out what the station coverage is, there's a graph-drawing tool that tells you.</p>
<pre><code>$ tools/server_query.py -q stats -c kpcc | tools/graph.py 

         +-0---1---2---3---4---5---6---7---8---9---10--11--12--13--14--15--16--17--18--19--20--21--22--23--+
2015-07-06 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . |
2015-07-07 *=******.*********************************************.**************************************** |
2015-07-08 ************************************************* **********************************************|
...
2015-08-02 **=*************************==************* .**** ********************************************* |
2015-08-03 *** ***** *********************************** ********* ******.** *** *******=======*********** |
2015-08-04 ********.**************************************************** . . . . . . . . . . . . . . . . . |
         +-0---1---2---3---4---5---6---7---8---9---10--11--12--13--14--15--16--17--18--19--20--21--22--23--+

         kpcc coverage: 90.877315%</code></pre>
<h3 id="being-a-client">Being a Client</h3>
<p>A client should be able to use the service in any reasonable way with any reasonable set of expectations. Furthermore, the client should be able to trust the service to take care of all reasonable problems within the service's scope.</p>
<p>That's always true, regardless of the service; we could be talking about banks or hookers here. But no, we are talking software - and yes, it still holds.</p>
<h4 id="easy-for-novices">Easy for novices</h4>
<p>If Alice doesn't really know how to use computers that well, there is a <a href="http://indycast.net">web front end</a> that explains what indycast is and has a simple and attractive user-interface that she can operate on the device of her choosing.</p>
<p>There's <a href="https://github.com/kristopolous/DRR/issues/104">three cognitively distinct</a> ways to think about indycast:</p>
<ul>
<li><strong>Podcaster</strong>: A service where you specify time slices to use</li>
<li><strong>DVR</strong>: You can start live radio in the past and then pause and scrub it.</li>
<li><strong>Concierge</strong>: Set an email reminder to listen to a show later.</li>
</ul>
<h5 id="whats-a-concierge">What's a Concierge?</h5>
<p>The Concierge service is the only one that ought to need explanation. Assume Alice is listening to a wonderful lecture, let's say <a href="http://media.bioneers.org/listing/intellectual-ecology-green-chemistry-and-biomimicry-john-warner/">Intellectual Ecology: Green Chemistry and Biomimicry</a> but it's on at an inconvenient time and she has things to do with her life.</p>
<p>She can <a href="http://indycast.net/reminder">set a reminder</a> which uses <code>localStorage</code> to remember her email address and the last station she selected.</p>
<p>There she has a convenient selection of specifying the current half hour, 1-hour, or 2-hour time slot. Then she can specify a note such as &quot;John Warner's subversive ideas on chemistry&quot;. And then, at some time later, an email gets sent back to her saying &quot;Hey here's the audio you requested with the notes your specified. Here's a download link&quot;.</p>
<p>In that way, it's a radio concierge service, looking out for you.</p>
<h5 id="convenient-for-all-levels-of-interaction">Convenient for all levels of interaction</h5>
<p>In <em>Getting Everything You Can Out of All You've Got</em>, Jay Abraham takes time to elaborate on what a <em>client</em> is ... outlining how it becomes a paternal relationship - creating a level of trust where your mindshare can be given away to another entity. A great product doesn't have customers, it has clients.</p>
<blockquote>
<p><em>client</em>: Anyone under the care of another. <small>Jay Abraham <em>Getting Everything You Can Out of All You've Got</em></small></p>
</blockquote>
<p>When designing software, it's often instructive to make yourself the first client. If you can't trust the solution to simplify your life and solve integral problems, then nobody else should either.</p>
<p>Given that, not only was this technology designed to be used by people who thumb around their smart-phones, but it was also designed for people who do Tux-cosplay at Linux conferences and think DefCon is full of posers. (<em>ahem</em>, <em>cough cough</em>, me)</p>
<p>If you are a hacker, read on. Alice is a hacker. She has no problem using a command line.</p>
<h2 id="makes-hackers-do-the-splits-while-shooting-party-poppers">Makes hackers do the splits while shooting <a href=http://i.dailymail.co.uk/i/pix/2014/12/21/24333D7D00000578-0-image-m-13_1419157979609.jpg>party poppers</a></h2>
<p>The first thing that Alice does is <code>curl</code> the main indycast site.</p>
<p>Normally this is a stupid idea as she would get a bunch of terribly formatted server-generated HTML, but not with indycast! Here is what she sees:</p>
<pre><code>$ curl http://indycast.net/    
The current stations are healthy:

 * http://indycast.net/kcrw/
 * http://indycast.net/kdvs/
 ...
 * http://indycast.net/wxyc/
 * http://indycast.net/wzrd/

Query the /help end-point to see
supported features on a per-station basis.

Thanks for using curl/7.26.0 ;-).
$</code></pre>
<p>Finally someone cares about the hackers. She can easily copy and paste the stubs to access the API.</p>
<h4 id="subscribe-to-any-show">Subscribe to any show</h4>
<p>XMLs podcasts feed are generated with a simple url schema:</p>
<pre><code>http://indycast.net/[station]/[weekday,...]/[start time]/[duration]/[name]</code></pre>
<p>Let's say there's a 2 hour show called, say <em>Darkwaves</em> at 2AM Monday and Wednesday mornings, you could do:</p>
<pre><code>http://indycast.net/kpcc/mon,wed/2am/2hr/Darkwaves.xml</code></pre>
<p>That URL would happily works with anything that ostensibly accepts so-called <em>podcasts</em>.</p>
<p>What if you don't use a podcaster? What if you use something that accepts m3u files? Fine then,</p>
<pre><code>http://indycast.net/kpcc/mon,wed/2am/2hr/Darkwaves.m3u</code></pre>
<p>Alright, what about pls?</p>
<pre><code>http://indycast.net/kpcc/mon,wed/2am/2hr/Darkwaves.pls</code></pre>
<p>Or if you prefer, since the XML gets printed in a human readable pretty-print format, we can just cut the BS and do something like this:</p>
<pre><code>$ curl -s kxlu.indycast.net:8890/sun/7pm/1hr/show.xml | grep enclosure 
  &lt;enclosure url=&quot;http://kxlu.indycast.net:8890/slices/kxlu-201507261900_62.mp3&quot; length=&quot;59520000&quot; type=&quot;audio/mpeg&quot;/&gt;
  &lt;enclosure url=&quot;http://kxlu.indycast.net:8890/slices/kxlu-201508021900_62.mp3&quot; length=&quot;59520000&quot; type=&quot;audio/mpeg&quot;/&gt;

# or maybe
$ curl -s kxlu.indycast.net:8890/sun/7pm/1hr/show.m3u | grep -v \# | xargs mplayer</code></pre>
<p>Like a boss. Alice is a boss.</p>
<p>BTW, the audio intentionally starts a bit early and goes a bit over because in the real world, shows don't end on some exact NTP millisecond.</p>
<h3 id="rewind-pause-and-scrub-live-radio">Rewind, pause, and scrub live radio</h3>
<p>Alice turns on her radio and there's a fascinating interview going on. Unfortunately, she missed the beginning of it. Luckily, she is able to listen to KPCC starting say, 5 minutes ago, by doing the following:</p>
<pre><code>$ mplayer http://indycast.net/kpcc/live/-5min</code></pre>
<p>Or, if she wants to listen starting at 1pm, this works:</p>
<pre><code>$ mpg321 http://indycast.net/kpcc/live/1pm</code></pre>
<h4 id="listen-to-user-specified-arbitrary-time-slices">Listen to user-specified arbitrary time slices</h4>
<p>If Alice just wants to listen to say, the Darkwaves show directly, from the command line, without all the hassle, she can specify a date, time, and duration, such as this:</p>
<pre><code>$ mplayer2 http://indycast.net/kpcc/at/monday_2am/2hr</code></pre>
<p>In fact, there's another more orthogonal way to do this, for Bob, who is forgetful and lazy:</p>
<pre><code>$ mpv http://indycast.net/kpcc/mon/2am/2hr</code></pre>
<p>See how this is similar to the podcast link of</p>
<pre><code>http://indycast.net/kpcc/mon/2am/2hr/Darkwaves.xml</code></pre>
<p>Simply by omitting the christening of the show and stopping after the duration, the server figures you just want the most recent episode and gives it to you. How nice for Bob.</p>
<h2 id="fast-and-small">Fast and small</h2>
<h3 id="disk-space-efficient">Disk space efficient</h3>
<p>VPSs generally don't give that much disk space and archiving audio would normally take a lot of it.</p>
<p>There's two systems here. You can put your server in <a href="https://github.com/kristopolous/DRR/wiki/Join-the-Federation">on-demand mode</a>, which means that lots of things can't be done (basically, just forward-moving subscriptions), or you can use cloud storage.</p>
<p>A survey was done in July 2015 to try to find the cheapest storage options:</p>
<ul>
<li>Amazon EC2: $0.050 / GB</li>
<li>Google Compute: $0.040 / GB</li>
<li>Microsoft Azure: $0.024 / GB</li>
</ul>
<p>Coming in at less than half the price of EC2, MS Azure was the obvious choice. If configured with credentials, the server will use an Azure account to offload the valuable disk space on the VPS. If you would rather use another service, <a href="https://github.com/kristopolous/DRR/issues">open a bug</a>.</p>
<p>A tool <code>tools/cloud.py</code> computes the current cost for the stations specified. Also, a tool <code>tools/cleanup_cloud.sh</code> will analyze all the content on the cloud and make sure that it's valid and in use by looking at a recent backup and doing a station-by-station comparison. Here is an example:</p>
<pre><code>$ tools/cloud.py

 Station   Files   Space (GB)
-----------------------------
14: kcrw   1738    22.467
13: kdvs   1938    25.881
...
 2: wxyc   1114    14.798
 1: wzrd   1038     3.368
-----------------------------
 Total    30359   307.282 GB
 Cost     $7.37/month

 *using $0.024/GB azure pricing</code></pre>
<h3 id="cpu-efficient">CPU efficient</h3>
<p>There is <strong>no conventional audio processing done</strong> on the server. No ffmpeg, avconv, lame, mencoder. No none of that. It can all be cleverly avoided - lemee 'splain:</p>
<p>Because audio streams are just binary files, and the binary files are identical independent of the user downloading them, then in order to overlap or splice the audio all you need is the ability to parse and find the headers ... not the payloads themselves.</p>
<p>In order to find matching payloads, you can look at a sequence of bytes, called a signature, at the beginning of the payloads, and simply match that. No audio-fingerprinting or FFT between time and frequenc... no none of that. It's much faster.</p>
<blockquote>
<p>A blazingly fast and unique approach to audio-processing. <small>Indycast author, <em>Specious Claims &amp; Unfounded Hype</em></small></p>
</blockquote>
<p>But since there was no library out there that did just this, it was hand-rolled (see <a href="https://github.com/kristopolous/DRR/blob/master/server/lib/audio.py">server/lib/audio.py</a>). It scans headers, hopping around the file, making a number of bold assumptions about things (such as CBR encoding) and as a result, audio can be brought down from the cloud storage, stitched together, and then sliced in under a second.</p>
<p>The audio processing engine wasn't designed to process all types of MP3 and AAC files but it was instead designed to deal with broken headers, files that are cut off, that begin in the middle of a payload, etc.</p>
<p>Being able to deal with broken files in the real world without <em>freaking out</em> is always more useful than supporting arcane obscure parts of a format that were written by the standards body and then promptly forgotten about the next day.</p>
<p>Bitrates in fact, are computed based on the rate of the bits transiting over the connection in a given duration as opposed to being internally taken from what the file says it is.</p>
<p>This is a much more direct and format agnostic computation. The sample size is large enough to avoid any errors (in fact, for HE-AAC+ streams, it performs more accurate duration measurements then <code>ffprobe</code> ... really).</p>
<h3 id="offloaded-dependencies">Offloaded dependencies</h3>
<p>When things would take too many dependencies, the task was intentionally off-loaded to the main website in order to minimize the complexity and responsibilities behind running a server. The server has a distinct and unique purpose in life.</p>
<p>But that doesn't stop us from our fun hacking.</p>
<h4 id="restful-logo-generation">Restful logo generation</h4>
<p>Logos for the podcasts are generated server-side at indycast.net so as not to require any image-processing or font dependencies on the servers themselves. The background tint is chosen based on the word itself in order to create a diverse but distinct palette for the various logos.</p>
<p>The schema for generating them looks like the following</p>
<pre><code>http://indycast.net/icon/(Arbitrary_string)_(size).png</code></pre>
<p>For instance:</p>
<pre><code>&lt;img src=http://indycast.net/icon/Here+is+one_120.png&gt;
&lt;img src=http://indycast.net/icon/And+here+is+another_120.png&gt;
&lt;img src=http://indycast.net/icon/You+can+go+small_90.png&gt;</code></pre>
<p>Looks like so:</p>
<div id="logo-block">
<p><img src=http://indycast.net/icon/Here+is+one_120.png><img src=http://indycast.net/icon/And+here+is+another_120.png><img src=http://indycast.net/icon/You+can+go+small_90.png></p>
</div>
<p>The logos are 16-color PNGs which make them small and fast (although admittedly kind of ugly).</p>
<h4 id="share-this-with-the-world-or-not.">Share this with the world, or not.</h4>
<p>If you want it all for yourself, it's easy to run your own network of servers for personal private use - you can easily stuff 25 stations on any modern consumer-grade internet connection. Each instance takes up about 80MB of resident memory so we are still just talking 2GB for all that.</p>
<p>Anarchy with a small <em>a</em>. Let's try it.</p>
<h3 id="making-things-suck-less.">Making things suck less.</h3>
<p>This technology has been a total game-changer in the way I listen to radio. Really.</p>
<p>In writing this software I wanted to have something that worked and follows principles in usability, transparency, adaptability, and simplicity that are held dearly by me. I've tried to create this in the way that I want software to be written.</p>
<p>Given that, I hope you enjoyed reading this and use indycast. I've been working full-time, 7 days a week on it since June 2015 and encourage you to become part of the community.</p>
<p>If there are stations you'd like to support, or better yet, money you'd like to donate, <a href="https://github.com/kristopolous/DRR/wiki">a wiki has been set up</a> describing:</p>
<ul>
<li>How to run your own server</li>
<li>The current cost and server architecture</li>
</ul>
<p>I also encourage you to <a href="https://github.com/kristopolous/DRR">pull down the code</a> which I have taken a serious effort on to be consistent and well-documented. If you find issues, please feel free to send a pull-request.</p>
<p>Thanks for reading.</p>
<p>~chris.<br/>August, 2015</p>
<script src="//code.jquery.com/jquery-1.11.3.min.js"></script>
<script src="/assets/js/demo.js"></script>
<script src="http://releases.flowplayer.org/js/flowplayer-3.2.13.min.js"></script>
<script src="http://releases.flowplayer.org/js/flowplayer.controls-3.2.11.min.js"></script>
