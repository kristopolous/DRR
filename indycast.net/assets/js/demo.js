var 
  is_first = true,
  use_fallback = false,
  station_list = [],
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

function set_fallback(url) {
  $f("radio-widget", "http://releases.flowplayer.org/swf/flowplayer-3.2.18.swf", {
    clip: {
      url: url,
      provider: 'audio'
    },
    plugins: {
      controls: {
        height: 30,
        autoHide: false
      },
      clip: {
        autoPlay: !is_first,
      },
      audio: {
        url: "flowplayer.audio-3.2.11.swf"
      }
    }
  });
  is_first = false;
}

function set_player(url) {
  $("#url").html(url);
  if(use_fallback) {
    set_fallback(url);
    return;
  }

  var audio = document.getElementById('radio-control');

  audio.src = url;
  
  audio.addEventListener('error', function() {
    $("#radio-widget").empty().css('height', '30px');
    use_fallback = true;
    is_first = true;
    set_fallback(url);
  });

  // Don't auto-play
  if (!is_first) {
    audio.play();
  }

  is_first = false;
}

function random_url(){
  var 
    station = random.station(),
    day = random.day(),
    duration = random.duration();

  //if(random.num() == 0) {
    return 'http://indycast.net/' + station + '/live/' + random.time();
  //} else {
  //  return 'http://indycast.net/' + [station, day, random.time(), duration].join('/');
  //}
}

$(function(){
  $.getJSON('/api/stations', function(list) {
    for (var ix = 0; ix < list.length; ix++) {
      console.log(list[ix]);
      station_list.push(list[ix].callsign);
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
