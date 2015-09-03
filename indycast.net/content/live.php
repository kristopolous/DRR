<link rel="stylesheet" href="/assets/css/main.css" />
<link href='http://fonts.googleapis.com/css?family=Inconsolata' rel='stylesheet' type='text/css'>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<style>
#now{ font-size: 4em }
</style>
<h1>Indycast TiVo<br/>
Pause, Rewind, Fast Forward live radio.</h1>
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
      <div id="text-container">
        <div class="box alt container">
          <div id=now></div>
          <button class='button'>5min ago</button>
          <button class='button'>10min ago</button>
          <button class='button'>15min ago</button>
          <br>
          <button class='button'>Starting at 12:30</button>
          <button class='button'>Starting at 12:00</button>
          <br>
          <audio src="http://kpcc.indycast.net:8930/live/5pm" preload="auto" controls></audio>
          Listen in external player
        </div>
      </div>
    </div>
  </section>
</div>
<?= $emit_script ?>
<script>

function timeConvert(ts) {
  return ts.toLocaleString();
}

setInterval(function(){
  $("#now").html(timeConvert(new Date()));
}, 1000);
</script> 
