<link rel="stylesheet" href="/assets/css/main.css" />
<title>Indycast - A free technology that sends you MP3s of any radio show - at any time, right now.</title>
<div class='super-main' id="main">
  <h1>A DVR for Radio</h1>
  <span style=display:inline-block>
  <p>MP3 archives<br><?= count(active_stations()); ?> stations</p>
  <small style=display:block;line-height:1.4em;text-align:center><b>Subscribe to shows<br>Listen to what you missed</b></small>
  </span>
</div>
<div class="box alt container"><?
  if(!$callsign) { ?>
    <section class="feature left">
      <a href="#" class="imgbox image icon fa-signal"><div id="description"></div></a>
      <div class="content">
        <h3>Choose the station</h3>
        <div id='station-search-box'>
          <i class="fa fa-search"></i>
          <input type="text" placeholder="Search" id='station-query'>
        </div>
        <ul class="radio-group group" id="station"><? emit_active_stations(); ?></ul>
        <a href="#volunteer">Volunteer to add a station!</a>
      </div>
    </section>
  <? } ?>
  <section class="feature right">
    <a href="#" style=background:#737F77 class="imgbox image icon fa-clock-o"></a>
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
    <a href="#" style='background:#7B7F73' class="imgbox image icon fa-mobile"></a>
    <div class="content">
      <label for="name">Show's Name</label>
      <input class="text" type="text" name="name" id="name" value="" placeholder="ex. Alien Air Music" />
      <div id="podcast-done" class="disabled">
        <div id='podcast-container'>
          <div id="podcast-top"></div>
          <a id="podcast-url" class='big-button' href="javascript:show_download()">
            <div id='rss-img'>
              <i class="fa fa-headphones"></i>
            </div>
            <div id='rss-header'>
              <h3 id='rss-title'>&nbsp;Listen Now</h3>
            </div>
          </a>
          <div id="podcast-bottom"></div>
        </div>
      </div>
    </div>
  </section>
</div>

<div id="footer">
  <div class="container 75%">
    <header class="major last">
      <h2>About</h2>
    </header>
    <div style="text-align: left">
      <p>Due to their limited resources, much of independent radio is not syndicated or available after broadcast.  We want to enjoy the benefits of time-shifted programming on these stations.</p>

      <a name="volunteer"></a><h3>How it works</h3>
      <p>The web stream of the station is recorded, then saved and delivered for personal use.  Every station is a different server acting in a federation.</p>

      <h3>Who runs this</h3>
      <p>People like you. Voluntarily.</p>

      <h3>Join the Federation</h3>
      <p>Generally each station gets its own server. For instance, kxlu.indycast.net and kdvs.indycast.net are different servers responsible for each station.</p>

      <p><a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation'>If you'd like to add or support a station, join the federation</a>.</p>

      <p>We also accept <a href=https://github.com/kristopolous/DRR/wiki/How-To-Donate>donations of VPS nodes</a> and money. Thanks for supporting indy radio in the 21st century.
      <div class="active-list">
        <a href='https://github.com/kristopolous/DRR/wiki/Join-the-Federation' class='button'>Join The Federation</a>
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
<div id="dialog">
  <div class="modal fade" id="dialog-choose">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
          <h4 class="modal-title" id='dialog-title'>Latest Episode</h4>
        </div>
        <div class="modal-body" id="podcast-dialog"></div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="dialog-email">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
          <h4 class="modal-title" id='dialog-title'>Get your show by email</h4>
        </div>
        <div class="modal-body" id="podcast-dialog">
          <label id='email-label' for="email">Email Address</label>
          <div>
            <input id='email-input' placeholder='ex: user@example.com' type='email' name='email'>
          </div>
          <p>Every week, you'll get a free download link to the most recent episode.</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-link" data-dismiss="modal">Not Interested</button>
          <button type="button" onclick="email_subscribe()" class="btn btn-primary">Get Free MP3s</button>
        </div>
      </div>
    </div>
  </div>

</div>

<div id='template-list'>
  <script type='text/template' id='tpl-top'>
    <span id='rss-note'>
      <h3><%= name %></h3>
      <% if (phrase) { %>
        <p><%= phrase %></p>
      <% } %>
    </span>
  </script>

  <script type='text/template' id='tpl-bottom'>
    <% if (is_ready) { %>
     <span id="rss-post">
       Listen to "<em><%= showname %></em>" which airs <%= day %> at <%= time %> on <%= station.toUpperCase() %>. No Ads. No strings attached. 100% Free.
     </span>
    <% } %>
  </script>

  <script type='text/template' id='tpl-dialog'>
    <div id="radio-index">
      <div id='radio-widget'>
        <div id='html5-widget'>
          <audio id="radio-control" controls type='audio/mpeg'>
        </div>
        <div id="flash-widget"></div>
      </div>
      <div style='text-align:right'>
        <a target=_blank class="btn btn-md btn-default" href="https://twitter.com/intent/tweet?text=<%=tweet_text%>" title="Share this on twitter">
        <i class="fa fa-twitter"></i>
        </a>
        <a href="<%= live_url %>" title="Download this to your device" class='btn btn-lg btn-link'><i class="fa fa-download"></i> Download </a>
      </div>
    </div>

    <div class='well'>
      <h5>Get <%= showname %> Weekly for free!</h5>
      <div id='dl-buttons'>
        <a target=_blank href='<%= podcast_url %>' class='btn btn-lg btn-default'><i class="fa fa-apple"></i> In iTunes</a>
        <a target=_blank href='<%= podcast_url %>' class='btn btn-lg btn-default'><i class="fa fa-rss-square"></i> In another podcaster</a>
        <a target=_blank href='<%= podcast_html_url %>' class='btn btn-lg btn-default'><i class="fa fa-globe"></i> In your browser</a>
        <!--<button data-toggle="modal" data-target="#dialog-email" type='button' class='btn btn-lg btn-default'><i class="fa fa-envelope"></i> Emailed to me</button>-->
      </div>
    </div>
  </script>
</div>

<?= $emit_script ?>
<!--[if lte IE 8]><script src="/assets/js/ie/respond.min.js"></script><![endif]-->
<script src="/assets/js/index.js"></script>
<? if ($callsign) { ?>
  <script> ev('station', '<?= $callsign ?>'); </script>
<? } ?>
