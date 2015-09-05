<link rel="stylesheet" href="/assets/css/main.css" />
<style>
#player-link { color: white }
#radio-container { text-align:center }
.disabled #radio-random { opacity: 0.4 }
#instructions { display: none }
.disabled #instructions { display: block }
.box { margin-bottom: 0 }
#half-hour,#whole-hour { display: none }
</style>
<div id="main">
  <h1>Indycast TiVo<br/>
  Pause, Rewind, Fast Forward live radio.
<br/>
<small>(under development 2015-09-05)</small>
</h1>
  <div class="box alt container">
    <section class="feature left">
      <div class="content">
        <label for="station">What station?</label>
        <div id="station-preselect"></div>
        <ul class="radio-group group" id="station"><?php
          foreach(active_stations() as $station) {
            echo '<li><a desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
          }
        ?></ul>
      </div>
      <div class="content">
        <label for="station">How Long Ago?</label>
        <div id='start_time' class="box alt radio-group group">
          <a class='button'>5 min</a>
          <a class='button'>10 min</a>
          <a class='button'>15 min</a>

          <label for="station">Or choose a specific time</label>
          <a id='half-hour' class='button'></a>
          <a id='whole-hour' class='button'></a>
        </div>
      </div>
      <div id='radio-container' class='disabled'>
        <span id='instructions'>Select the station and time above and then you can listen here.</span>
        <div id="radio-random">
          <div id='radio-widget'>
            <div id='html5-widget'>
            <audio id="radio-control" controls type='audio/mpeg'>
            </div>
            <div id="flash-widget">
            </div>
          </div>
          <a id="player-link">Listen with an external player</a>
        </div>
      </div>

    </section>
  </div>
</div>
<?= $emit_script ?>
<script src="//releases.flowplayer.org/js/flowplayer-3.2.13.min.js"></script>
<script src="//releases.flowplayer.org/js/flowplayer.controls-3.2.11.min.js"></script>
<script>

function to_numeric(number) {
  var my_date = new Date(number * 1000);
  return my_date.toLocaleTimeString().replace(':00 ', ' ');
}

var 
  html5_audio,
  markers = time_markers(),
  last_half_hour = to_numeric(markers.last_half_hour.start_time),
  ev = EvDa({start_time:'',station:''}),
  current_half_hour = to_numeric(markers.current_half_hour.start_time),
  current_hour = to_numeric(markers.current_hour.start_time);

$(function(){
  html5_audio = document.getElementById('radio-control');
  if(current_half_hour != current_hour) {
    $("#whole-hour").html(current_hour).css('display','inline-block');
  }
  $("#half-hour").html(current_half_hour).css('display','inline-block');

  easy_bind(['station', 'start_time']);
});

ev('', function(map) {
  if(map.station && map.start_time) {
    $("#radio-container").removeClass('disabled');
    var url = set_player('http://indycast.net/' + map.station + '/live/' + map.start_time.replace(' ',''));
    $("#player-link").attr({href: url});
  }
});

function timeConvert(ts) {
  return ts.toLocaleString();
}

</script> 
