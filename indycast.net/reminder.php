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
    <div id="main">

      <header class="major container 75%">
        <h2>
        Set a Reminder
        </h2>
      </header>
      <div class="box alt container">
        <section class="feature left">
          <div class="content">
  <label for="email">Email to Remind</label>
  <input type='email' name='email'>
  <label for="duration">What period?</label>
  <ul class="week-group group" id="duration">
    <li><a data="30" class="button">Current half hour</a></li>
    <li><a data="1hr" class="button">Current hour</a></li>
    <li><a data="1hr30" class="button">Custom</a></li>
  </ul>
          </div>
          <div class="content">
            <h3>Choose the station</h3>
            <div id='station-search-box'>
              <i class="fa fa-search"></i>
              <input type="text" placeholder="Search" id='station-query'>
            </div>
            <ul class="radio-group group" id="station"><?php
              foreach(active_stations() as $station) {
                echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
              }
            ?></ul>
            <a href="#volunteer">Volunteer to add a station!</a>
          </div>
        </section>
      </div>
<form method='post'>
  <div id="callsign-preselect">
    Show the callsign if previously set
  </div>

  <label for="notes">Notes</label>
  <input type='text' name='notes'>
  <button>Send me a reminder</button>
</form>
    </div>
    <div id="footer">
      <div class="container 75%">

        <header class="major last">
          <h2>About</h2>
        </header>
        <div style="text-align: left">
<p>Listening to something right now but have to run and don't have the time to finish it?</p>
<p>Miss the beginning of something and want to catch it later?</p>
<h3>We'll send you a reminder with a link to the audio. For free of course.</h3>

<p>You can even leave notes for your future-self telling yourself why you think it's so awesome.</p>
<p>Later on, when the show is over, an email will be sent to you with a link and the notes you leave.</p>

<p><b>Privacy policy:</b> We don't collect email addresses and we delete everything from our database after we send the email off to you.  Don't worry, we're on your side!</p>


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
