<?php 
include_once('common.php'); 
?>
<h2>Set a reminder</h2>
<p>Listening to something right now but have to run and don't have the time to finish it?</p>
<p>Miss the beginning of something and wnat to catch it later?</p>
<h3>We'll send you a reminder with a link to the audio. For free of course.</h3>

<p>Simply tell the email you'd like to use, the station you are listening to and pick a time slot</p>
<p>You can even leave notes for your future-self telling yourself why you think it's so awesome.</p>
<p>Later on, when the show is over, an email reminder will be sent to you with a link and the notes you leave.</p>

<p><b>Privay policy:</b> We don't collect email addresses and we delete everything from our database after we send the email off to you.  Don't worry, we're on your side!</p>

<form method='post'>
  <input type='email' name='email'>
  <div id="callsign-chooser">
    <div id="callsign-preselect">
      Show the callsign if previously set

      change callsign link
    </div>
    <div id="callsign-menu">
      get the active stations
    </div>
  </div>

  <input type='text' name='callsign'>
  suggestions of blocks of time
  We presume that the time is local (although we will normalize it if it isn't) so
  we just find the closest half hour and hour mark ... 
  <input type='text' name='notes'>
  <button>Send me the link later</buton>
</form>

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
