Listen to your station live or 

Pick your station
How many minutes ago do you want to start from?

Pick a specific time

You can listen to it using the player below or
you can click here for an external player
<?php
include_once('common.php');
?>
<!doctype html5>
<style>
#now{ font-size: 4em }
button { font-size: 2em }
</style>
Pause, Rewind, Fast Forward live radio.
In the browser or using an external player.
<div id=now></div>
            <ul class="radio-group group" id="station"><?php
              foreach(active_stations() as $station) {
                echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
              }
            ?></ul>
<button>5min ago</button>
<button>10min ago</button>
<button>15min ago</button>
<br>
<button>Starting at 12:30</button>
<button>Starting at 12:00</button>
<br>
<audio src="http://kpcc.indycast.net:8930/live/5pm" preload="auto" controls></audio>
<script src="//code.jquery.com/jquery-1.11.3.min.js"></script>
<script>

function timeConvert(ts) {
  return ts.toLocaleString();
}

setInterval(function(){
  $("#now").html(timeConvert(new Date()));
}, 1000);
</script> 
