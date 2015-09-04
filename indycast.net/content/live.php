<link rel="stylesheet" href="/assets/css/main.css" />
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
      <label for="station">How Long Ago?</label>
      <div id="text-container">
        <div class="box alt container radio-group">
          <button class='button'>5min ago</button>
          <button class='button'>10min ago</button>
          <button class='button'>15min ago</button>

        <label for="station">Or choose a specific time</label>
          <button class='button'>Starting at 12:30</button>
          <button class='button'>Starting at 12:00</button>
          <br>
        </div>
      </div>
    </div>
    <div id="radio-random">
      <h2 id="url"></h2>
      <div id='radio-widget'>
        <div id='html5-widget'>
        <audio id="radio-control" controls type='audio/mpeg'>
        </div>
        <div id="flash-widget">
        </div>
      </div>
      <a>Listen in external player</a>
    </div>

  </section>
</div>
<?= $emit_script ?>
<script>

function timeConvert(ts) {
  return ts.toLocaleString();
}

</script> 
