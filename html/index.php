<?php
include_once('db.php');
?>
<!DOCTYPE HTML>
<html>
  <head>
    <title>Indycast - Podcasting The World's Independent Radio</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--[if lte IE 8]><script src="assets/js/ie/html5shiv.js"></script><![endif]-->
    <link rel="stylesheet" href="assets/css/main.css" />
    <!--[if lte IE 8]><link rel="stylesheet" href="assets/css/ie8.css" /><![endif]-->

    <meta name="description" content="The world's independent radio - podcasted." />
    <meta property="og:site_name" content="Indycast" />
    <meta property="og:url" content="http://indycast.net" />
    <meta property="og:title" content="Indycast - Podcasting the World's Independent Radio" />
    <meta property="og:type" content="website" />
    <meta property="og:description" content="Subscribe to your favorite shows. Listen on your time, not airtime." />
    <meta property="og:image" content="http://indycast.net/og-image.php" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:site" content="@indycaster" />
    <meta name="twitter:creator" content="@indycaster" />
    <meta name="twitter:title" content="Indycast - Podcasting the World's Independent Radio" />
    <meta name="twitter:url" content="http://indycast.net" />
    <meta name="twitter:description" content="Subscribe to your favorite shows. Listen on your time, not airtime." />
    <meta name="twitter:image:src" content="http://indycast.net/images/twit-image.jpg" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="favicon.ico" >
  </head>
  <body>
    <div id="header">
      <h1>Indycast Radio</h1>
      <p>Podcasting the World's Independent Radio</p>
    </div>

    <div id="main">

      <header class="major container 75%">
        <h2>
        Subscribe to your favorite shows.
        <br />
        Listen on your time, not airtime.
        </h2>
      </header>

      <div class="box alt container">
        <section class="feature left">
          <a href="#" class="image icon fa-signal"><img src="images/pic01.jpg" alt="" /><div id="description"></div></a>
          <div class="content">
            <h3>Choose the station</h3>
            <ul class="radio-group group" id="station">
<?php
  foreach(active_stations() as $station) {
    echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li> ';
  }
?>
            </ul>
            <a href="#volunteer">Volunteer to add a station!</a>
          </div>
        </section>
        <section class="feature right">
          <a href="#" class="image icon fa-clock-o"><img src="images/pic02.jpg" alt="" /></a>
          <div class="content">

            <label for="day">day of week to record on</label>
            <ul class="week-group" id="day">
              <li><a class="button">sun</a></li>
              <li><a class="button">mon</a></li>
              <li><a class="button">tue</a></li>
              <li><a class="button">wed</a></li>
              <li><a class="button">thu</a></li>
              <li><a class="button">fri</a></li>
              <li><a class="button">sat</a></li>
            </ul>
            <div id='time'>
              <label for="start">Starting at</label>
              <input class="text" size=4 type="text" name="start" id="start" value="" placeholder="ex: 3:30 PM" />

              <ul class="week-group group inline" id="ampm">
                <li><a class="button">am</a></li>
                <li><a class="button">pm</a></li>
              </ul>

            </div>
            <label for="duration">For how long</label>
            <ul class="week-group group" id="duration">
              <li><a data="30min" class="button">30 min</a></li>
              <li><a data="1hr" class="button">1 hr</a></li>
              <li><a data="1hr30" class="button">1&frac12; hrs</a></li>
              <li><a data="2hr" class="button">2 hrs</a></li>
            </ul>
          </div>
        </section>
        <section class="feature left">
          <a href="#" class="image icon fa-mobile"><img src="images/pic03.jpg" alt="" /></a>
          <div class="content">
            <h3>Give it a name</h3>
            <label for="name">Show Name</label>
            <input class="text" type="text" name="name" id="name" value="" placeholder="ex. Alien Air Music" />
          </div>
        </section>
      </div>

      <footer class="major container">
        <div id="podcast-done">
          <h3>Your podcast link</h3>
          <a id="podcast-url"></a>
        </div>
        <div id="podcast-notdone">
          <h3>The podcast will appear here</h3>
          <p>Please select desired day, station, and time above</p>
        </div>
      </footer>

    </div>

    <div id="footer">
      <div class="container 75%">

        <header class="major last">
          <h2>About</h2>
        </header>
        <div style="text-align: left">
          <p>Due to their limited resources, much of independent radio is not syndicated or available after broadcast.  We want to enjoy the benefits of time-shifted programming on these stations.</p>

          <a name="volunteer"></a><h3>How it works</h3>
          <p>The web stream of the station is recorded and then saved and delivered for personal use.  Every station is a different server which acts in a federation.</p>

          <h3>Who runs this</h3>
          <p>People like you. Voluntarily.</p>

          <h3>Join the Federation</h3>
          <p>Generally each station gets its own server.  For instance, kxlu.indycast.net and kdvs.indycast.net are different servers responsible for each station.</p>

          <p><a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation'>If you'd like to add or support a station, join the federation</a>.</p>

          <p>We also accept <a href=https://github.com/kristopolous/DRR/wiki/How-To-Donate>donations of VPS nodes</a> and money. Thanks for supporting indy radio in the 21st century.
          <div class="active-list">
            <a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation' class='button'>Join The Federation</a> or
            <a name="donate"></a>
            <form action="https://www.paypal.com/cgi-bin/webscr" method="post" id="donate">
              <input type="hidden" name="cmd" value="_s-xclick">
              <input type="hidden" name="hosted_button_id" value="X4J4BD86VTXWS">
              <input class="button" type="submit" value="Donate via PayPal" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
              <img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
            </form>
          </div>
        </div>

        <header class="major last">
          <h2>Questions or comments</h2>
        </header>

        <p>For questions, comments, or to report a device that isn't supported, please <a href="mailto:indycast@googlegroups.com">send an email</a> to <a href="https://groups.google.com/d/forum/indycast">the mailing list</a>. Thanks!</p>

        <ul class="icons">
          <li><a href="https://twitter.com/indycaster" class="icon fa-twitter"><span class="label">Twitter</span></a></li>
          <li><a href="http://github.com/kristopolous/DRR/" class="icon fa-github"><span class="label">Github</span></a></li>
        </ul>

        <ul class="copyright">
          <li>This is an <a href="https://github.com/kristopolous/DRR">open source project</a>.</li><li>Design: <a href="http://html5up.net">HTML5 UP</a></li>
        </ul>

      </div>
    </div>
    <script type='text/template' id='tpl-podcast'>
      <span id='rss-top'>
        <span>
          <img src='images/rss_64.png'>
        </span>
        <span id='rss-header'>
          <h3 id='rss-title'><%= name %></h3>
          <span id='rss-time'><%= day %> at <%= time %> on <%= station %></span>
        </span>
      </span>
      <span id='podcast-link'>
        <%= parts.join(' <br> ') %>
      </span>
    </script>

    <script src='assets/js/underscore-min.js'></script>
    <script src="assets/js/jquery.min.js"></script>
    <script src="assets/js/skel.min.js"></script>
    <script src="assets/js/util.js"></script>
    <script src="assets/js/evda.js"></script>
    <!--[if lte IE 8]><script src="assets/js/ie/respond.min.js"></script><![endif]-->
    <script src="assets/js/main.js"></script>

    <script>
    var 
      ev = EvDa({start: '', name: '', station: '', ampm: '', day: []}),
      fullName = {
        sun: 'Sundays', mon: 'Mondays', tue: 'Tuesdays', wed: 'Wednesdays',
        thu: 'Thursdays', fri: 'Fridays', sat: 'Saturdays'
      },
      tpl = {},
      time_re = /^\s*(1[0-2]|[1-9])(:[0-5][0-9])?\s*([ap]m)?\s*$/i;


    ev('ampm', function(val){
      if(val) {
        $("#start").val($("#start").val().replace(/\s*([ap]m)\s*/i, val))
      }
    });

    ev('', function(map) {
      var start_time;

      for(var key in map) {
        $("#" + key + " a").removeClass("selected");

        if(key == 'day') {
          _.each(map[key], function(what) {
            $("#" + key + " a:contains(" + what + ")").addClass("selected");
          });
        } else if(key != 'name') {
          $("#" + key + " a:contains(" + map[key] + ")").addClass("selected");
          $("#" + key + " a[data='" + map[key] + "']").addClass("selected");
        }

      }

      if(map.station && map.ampm && map.day && map.day.length && map.start && map.duration) {
        if (!map.name) {
          map.name = 'stream';
        }

        map.station = map.station.toLowerCase();

        // #27: dump the spaces, make it lower case and avoid a double am/pm
        start_time = map.start.replace(/\s+/,'').toLowerCase().replace(/[ap]m/, '') + map.ampm;

        url = 'http://' + [
          'indycast.net',
          map.station,
          map.day.join(',') + " ",
          start_time,
          map.duration,
          encodeURI(map.name).replace(/%20/g,'_')
        ].join('/') + ".xml";

        var parts = url.split(' '), 
          single = url.replace(/\s/,''), 
          fullday;
          _map = _.map(map.day, function(what) { return fullName[what] });

        if(map.day.length == 1) {
          fullday = _map[0];
        } else {
          fullday = _map.slice(0, -1).join(', ') + ' and ' + _.last(_map);
        }

        $("#podcast-url").attr({'href': single }).html(
          tpl.podcast({
            name: (map.name || ''),
            day: fullday,
            time: start_time,
            station: map.station.toUpperCase(),
            single: single,
            parts: parts
          })
        );

        $("#podcast-notdone").hide();
        $("#podcast-done").show();
      } else {
        $("#podcast-url").html("Please select options above");
        $("#podcast-notdone").show();
        $("#podcast-done").hide();
      }

    });

    ev.test('start', function(v, cb, meta) {
      var res = time_re.test(v);
      
      if(res) {
        if(/[ap]m/.test(v)) {
          ev('ampm', v.slice(-2));
        } 
      } 
       
      $(meta.node)[(res ? 'remove' : 'add') + 'Class']('error');
      cb(res);
    });

    function htmldo(what) {
      // hyperlinking
      what = what.replace(/[a-z]+:\/\/[^\s^<]+/g, '<a href="$&" target=_blank>$&</a>');

      // paragrapherizing
      what = what.replace(/\n/g, '</p><p>');

      // finalerizing
      return '<p>' + what + '</p>';
    }

    $(function() {
      tpl.podcast = _.template($("#tpl-podcast").html());

      $(".radio-group a").hover(function(){
        $("#description").html("<h2>" + this.innerHTML + "</h2>" + htmldo(this.getAttribute('desc'))).show();
      });

      // #23 - multiday recordings
      $("#day a").click(function(){
        ev.setToggle('day', this.innerHTML);
      });

      $(".group a").click(function(){
        var node = $(this).parentsUntil("div").last();
        ev(node[0].id, this.getAttribute('data') || this.innerHTML);
      });

      $("#start,#name").bind('blur focus change keyup',function(){
        ev(this.id, this.value, {node: this});
      });
      
      for(var el in {start:1,name:1}) {
        var $node = $("#" + el),
            val = $node.val();

        if(val) {
          ev(el, val, {node: $node.get(0)});
        }
      }
      
      ev.fire('start');
      ev.fire('name');

    });

    // #30: Da Goog!
    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
    (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
    m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
    })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

    ga('create', 'UA-28399789-2', 'auto');
    ga('send', 'pageview');

    </script>
  </body>
</html>
