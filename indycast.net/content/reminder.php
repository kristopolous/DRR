<meta name="description" content="Sending you audio for later enjoyment" />
<meta property="og:site_name" content="Indycast" />
<link rel="stylesheet" href="/assets/css/main.css" />
<link href='http://fonts.googleapis.com/css?family=Inconsolata' rel='stylesheet' type='text/css'>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<link rel="stylesheet" href="/assets/css/reminder.css" />
<div id="main">
  <h1>Indycast Reminders<br/>Listen later to what's on now</h1>

  <div class="box alt container">
    <section class="feature left">
      <div class="content">

        <label for="duration">What period?</label>

        <ul class="week-group group" id="duration">
          <li><a data="-30" class="button">Last<br/>half hour</a></li>
          <li><a data="30" class="button">Current<br/>half hour</a></li>
          <li><a data="60" class="button">Current<br/>hour</a></li>
        </ul>

        <div id="custom-time">
          <input id="start_time" type="text" placeholder="start time">
          <input id="end_time" type="text" placeholder="end time">
        </div>

        <label for="station">What station?</label>
        <div id="station-preselect"></div>
        <ul class="radio-group group" id="station"><?php
          foreach(active_stations() as $station) {
            echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
          }
        ?></ul>
      </div>
      <div class="content">
        <div id="text-container">

          <label id='email-label' for="email">Your Email</label>
          <div>
            <input id='email-input' type='email' name='email'>
          </div>

          <label for="notes">Show Notes</label>
          <div>
            <input type='text' name='notes' placeholder="To help remember what this is">
          </div>
        </div>
        <div id='podcast-url-container'>
          <div id="thanks">Thanks, we'll notify you when the show is over and ready for download.</div>
          <div id="err">Woops, unable to register this reminder. Please try again. If the problem persists, <a href=mailto:indycast@googlegroups.com>Email us</a> with details.</div>
          <a class='big-button disabled'>
            <span id='rss-top'>
              <div id='rss-img'>
                <i class="fa fa-envelope"></i>
              </div>
              <div id='rss-header'>
                <h3 id='rss-title'>Email me the MP3</h3>
              </div>
            </span>
          </a>
        </div>
      </div>
    </section>
  </div>
</div>
<div id="footer">
  <div class="container 75%">

    <header class="major last">
      <h2>About</h2>
    </header>

    <div style="text-align: left">
      <p>Listening to something right now but have to run and don't have the time to finish it? Miss the beginning of something and want to catch it later?</p>
      <h3>We'll send you a reminder with a link to the audio. (For free of course)</h3>

      <p>You can even leave notes for your future-self telling yourself why you think it's so awesome.</p>
      <p>Later on, when the show is over, an email will be sent to you with a link and the notes you leave.</p>

      <p><b>Privacy policy:</b> We don't collect email addresses and we delete everything from our database after we send the email off to you.  Don't worry, we're on your side!</p>
    </div>
    <ul class="icons">
      <li><a href="https://twitter.com/indycaster" class="icon fa-twitter"><span class="label">Twitter</span></a></li>
      <li><a href="http://github.com/kristopolous/DRR/" class="icon fa-github"><span class="label">Github</span></a></li>
    </ul>

    <ul class="copyright">
      <li>This is an <a href="https://github.com/kristopolous/DRR">open source project</a>.</li><li>Design: <a href="http://html5up.net">HTML5 UP</a></li>
    </ul>
  </div>
</div>
<?= $emit_script ?>
<!--[if lte IE 8]><script src="/assets/js/ie/respond.min.js"></script><![endif]-->
<script>
//
// 2 range suggestions 30 min, 1 hr are always offered.
// the 1 hour is always the current hour and the 30 minute
// is always the nearest 30 minute that is the present
//
// The most laborious invocation appears to be our best friend here.
// That's this one, from mdn:
//
// new Date(year, month[, day[, hour[, minutes[, seconds[, milliseconds]]]]]);
//
var
  isiDevice = navigator.userAgent.match(/ip(hone|od|ad)/i),
  listenEvent = isiDevice ? 'touchend' : 'click',
  ev = EvDa({
    // find out the local tz offset
    offset: (new Date()).getTimezoneOffset(), 
    start_time: '', 
    end_time: '', 
    duration: '30', 
    email: '', 
    notes: ''
  }),

  markers = time_markers(),

  current_hour = markers.current_hour,
  last_half_hour = markers.last_half_hour,
  current_half_hour = markers.current_half_hour;

ev.after('', function(map) {
  if(map.email && map.station && map.start_time && map.end_time) {
    $(".big-button").removeClass('disabled');
  } else {
    $(".big-button").addClass('disabled');
  }
});

$(function(){

  ev('duration', function(what) {
    if(what == '30') {
      ev(current_half_hour);
    } else if (what == '60') {
      ev(current_hour);
    } else if (what == '-30') {
      ev(last_half_hour);
    }
  });

  easy_bind(['email', 'notes', 'station', 'duration', 'start_time', 'end_time']);

  ev({
    duration: '30',
  });

  var what = easy_sync(['email', 'station', 'duration']);

  if(what.station) {
    $("#station-preselect")
      .html("Auto-selected from previous use: <b>" + what.station.toUpperCase() + "</b><br/>")
      .append($("<a>Select a different station</a>").click(station_select))
      .show()

  } else {
    station_select();
  } 

  $(".big-button").click(function(){
    if($(this).hasClass('disabled')) {
      return;
    }
    if(ev('duration') == 'custom') {
      ev('human_time', 'from ' + ev('start_time') + ' to ' + ev('end_time'));
    }

    $.post('/api/reminder', ev(''), function(res) {
      $('.big-button').slideUp();
      if(res != 'true') {
        $("#err").slideDown();
      } else {
        $("#thanks").slideDown();
      }
    });
  });

});

ev('duration', function(what, meta) {
  if(what == 'custom') {
    $("#custom-time").slideDown();
  } else if (meta.old == 'custom') {
    $("#custom-time").slideUp();
  }
});

</script>
