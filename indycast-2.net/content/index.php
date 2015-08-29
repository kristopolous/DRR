<?
include_once('../common.php');
?>
<link rel="stylesheet" href="/assets/css/main.css" />
<title>Indycast - A technology to record the radio that doesn't get podcasted</title>
<!--
  <header class="major container 75%">
    <h2>
    Subscribe to any broadcast
    <br />
    Just by knowing when it's on.
    </h2>
  </header>
-->
<div id="header">
  <h1>Indycast DVR</h1>
  <p>A free <a href="/about">technology</a> to record the <?= $callsign ? strtoupper($callsign) : "radio that doesn't get podcasted" ?>
  <?php if ($callsign) { ?><br/><small>(<a href="/">and more</a>)</small><?php } ?></p>
  <small>Works on your <?= $device ?>. No signup or app needed.</small>
</div>
<div class="box alt container"><?
  if(!$callsign) { ?>
    <section class="feature left">
      <a href="#" class="image icon fa-signal"><img src="/images/pic01.jpg" alt="" /><div id="description"></div></a>
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
  <? } ?>
  <section class="feature right">
    <a href="#" class="image icon fa-clock-o"><img src="/images/pic02.jpg" alt="" /></a>
    <div class="content" id='day-picker'>

      <label for="day">day(s) of week</label>
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
        <label for="start">Start time</label>
        <div id='time-controls'>
          <input class="text" size=4 type="text" name="start" id="start" value="" placeholder="ex: 3:30 PM" /><ul class="week-group group inline" id="ampm">
            <li><a class="button">am</a></li>
            <li><a class="button">pm</a></li>
          </ul>
        </div>
      </div>
      <label for="duration">duration</label>
      <ul class="week-group group" id="duration">
        <li><a data="30" class="button">30 min</a></li>
        <li><a data="1hr" class="button">1 hr</a></li>
        <li><a data="1hr30" class="button">1&frac12; hrs</a></li>
        <li><a data="2hr" class="button">2 hrs</a></li>
      </ul>
    </div>
  </section>
  <section class="feature left">
    <a href="#" class="image icon fa-mobile"><img src="/images/pic03.jpg" alt="" /></a>
    <div class="content">
      <h3>Give it a name</h3>
      <input class="text" type="text" name="name" id="name" value="" placeholder="ex. Alien Air Music" />
    </div>
  </section>
  <footer class="major container">
    <div id="podcast-done">
      <h3>My free subscription</h3>
      <a id="podcast-url" class='big-button disabled'></a>
    </div>
  </footer>
  </div>
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
      <p>Generally each station gets its own server. For instance, kxlu.indycast.net and kdvs.indycast.net are different servers responsible for each station.</p>

      <p><a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation'>If you'd like to add or support a station, join the federation</a>.</p>

      <p>We also accept <a href=https://github.com/kristopolous/DRR/wiki/How-To-Donate>donations of VPS nodes</a> and money. Thanks for supporting indy radio in the 21st century.
      <div class="active-list">
        <a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation' class='button'>Join The Federation</a> <span id='or'>or</span> 
        <a name="donate"></a>
<form action="https://www.paypal.com/cgi-bin/webscr" method="post" id="donate"><input type="hidden" name="cmd" value="_s-xclick"><input type="hidden" name="hosted_button_id" value="X4J4BD86VTXWS"><input class="button fit" type="submit" value="Donate via PayPal" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!"><img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1"></form>
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
    <div id='rss-img'>
      <img src='/images/rss_64.png'>
    </div>
    <div id='rss-header'>
      <h3 id='rss-title'><%= name %></h3>
      <span id='rss-time'><% if (phrase) { %><%= phrase %><% } else { %><%= day %> at <%= time %> on <%= station %><% } %></span>
    </div>
  </span>
  <span id='podcast-link'>
    <%= parts.join(' <br> ') %>
  </span>
</script>

<script src='//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.8.3/underscore-min.js'></script>
<script src="//code.jquery.com/jquery-1.11.3.min.js"></script>
<script src="/assets/js/evda.min.js"></script>
<!--[if lte IE 8]><script src="/assets/js/ie/respond.min.js"></script><![endif]-->
<script src="/assets/js/indycast.js"></script>
<? if ($callsign) { ?>
  <script> ev('station', '<?= $callsign ?>'); </script>
<? } ?>
