var 
  audio_count = 0,
  station_list = [],
  html5_audio,
  random = {
    num: function(max, min) {
      min = min || 0;
      max = max || 1;
      return Math.round(Math.random() * max + min);
    },
    time: function(){
       return random.num(11, 1) + ['am','pm'][random.num()];
    },
    day: function(){
      return ['sun','mon','tue','wed','thu','fri','sat'][random.num(7)];
    },
    duration: function() {
      var 
        in_minutes = random.num(9, 1) * 15, 
        ret = '';

      if(in_minutes > 60) {
        ret += Math.floor(in_minutes / 60) + 'hr'
      }

      if(in_minutes % 60) {
        ret += in_minutes % 60;
      }
      return ret;
    },
    station: function() {
      return station_list[random.num(station_list.length - 1)];
    }
  };

function do_random() {
  set_player(random_url());
}

function set_fallback(url, count) {
  $("#flash-widget").show();

  $f("flash-widget", "http://releases.flowplayer.org/swf/flowplayer-3.2.18.swf", {
    onError: function() {
      // this means that both the html5 and flash player failed ... so we
      // just move on to a new track.
      set_player(random_url());
    },
    clip: {
      url: url,
      provider: 'audio',
      live: true,
      autoPlay: count
    },
    plugins: {
      controls: {
        height: 30,
        fullscreen: false,
        autoHide: false
      },
      audio: {
        url: "flowplayer.audio-3.2.11.swf",
      }
    }
  });
}

function set_player(url) {
  var local = audio_count;

  $("#url").html(url);

  $("#flash-widget").hide();
  html5_audio.addEventListener('error', function() {
    $("#html5-widget").fadeOut();
    set_fallback(url, local);
  });

  html5_audio.addEventListener('loadstart', function(){
    $("#html5-widget").fadeIn();
  });

  html5_audio.src = url;

  // Don't auto-play if it's the first
  if (audio_count > 0) {
    html5_audio.play();
  }

  audio_count ++;
}

function random_url(){
  var 
    station = random.station(),
    day = random.day(),
    what_time = random.time(),
    duration = random.duration();

  //if(random.num() == 0) {
    return 'http://indycast.net/' + station + '/live/' + what_time;
  //} else {
  //  return 'http://indycast.net/' + [station, day, random.time(), duration].join('/');
  //}
}

$(function(){
  var callsign;

  html5_audio = document.getElementById('radio-control');

  $.getJSON('/api/stations', function(list) {
    for (var ix = 0; ix < list.length; ix++) {
      callsign = list[ix].callsign;
      station_list.push(callsign);
    }
    do_random();
  });
});

(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','//www.google-analytics.com/analytics.js','ga');

ga('create', 'UA-28399789-2', 'auto');
ga('send', 'pageview');
