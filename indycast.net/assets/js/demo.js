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
