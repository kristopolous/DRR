<?php 
include_once('common.php'); 
?>
<!DOCTYPE HTML>
<html>
  <head>
    <title>Indycast Reminders</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--[if lte IE 8]><script src="/assets/js/ie/html5shiv.js"></script><![endif]-->
    <link rel="stylesheet" href="/assets/css/main.css" />
    <!--[if lte IE 8]><link rel="stylesheet" href="/assets/css/ie8.css" /><![endif]-->
    <meta name="description" content="Sending you audio for later enjoyment" />
    <meta property="og:site_name" content="Indycast" />
    <link href='http://fonts.googleapis.com/css?family=Inconsolata' rel='stylesheet' type='text/css'>
    <link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
  </head>
  <body>


<style>
label { font-size: 0.8em}
</style>

<h2>Send a reminder</h2>
<form method='post'>
  <label for="email">Email</label>
  <input type='email' name='email'>
  <div id="callsign-chooser">
    <div id="callsign-preselect">
      Show the callsign if previously set

      change callsign link
    </div>
    <div id="callsign-menu">
      <ul class="radio-group group" id="station"><?php
        foreach(active_stations() as $station) {
          echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
        }
      ?></ul>
      get the active stations
    </div>
  </div>

  <input type='text' name='callsign'>
  suggestions of blocks of time
  We presume that the time is local (although we will normalize it if it isn't) so
  we just find the closest half hour and hour mark ... 
  <label for="notes">Notes</label>
  <input type='text' name='notes'>
  <button>Send me a reminder</button>
</form>
<h2>About</h2>
<p>Listening to something right now but have to run and don't have the time to finish it?</p>
<p>Miss the beginning of something and want to catch it later?</p>
<h3>We'll send you a reminder with a link to the audio. For free of course.</h3>

<p>Simply tell the email you'd like to use, the station you are listening to and pick a time slot</p>
<p>You can even leave notes for your future-self telling yourself why you think it's so awesome.</p>
<p>Later on, when the show is over, an email reminder will be sent to you with a link and the notes you leave.</p>

<p><b>Privay policy:</b> We don't collect email addresses and we delete everything from our database after we send the email off to you.  Don't worry, we're on your side!</p>


<script>
function ls(key, value) {
  if (arguments.length == 1) {
    return localStorage[key] || false;
  } else {
    localStorage[key] = value;
  }
  return value;
}

// 2 range suggestions 30 min, 1 hr are always offered.
// the 1 hour is always the current hour and the 30 minute
// is always the nearest 30 minute that is the present
var
  email = ls('email'),
  last_station = ls('last'),
  right_now = new Date(),
  last_minute = right_now.getMinutes() % 30;

  
</script>
