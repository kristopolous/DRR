<?php 
include_once('common.php'); 
?>
Set a reminder

Get user info, current time, last email, last station

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

var
  email = ls('email'),
  last_station = ls('last');

  
</script>
