//
// 2 range suggestions 30 min, 1 hr are always offered.
// the 1 hour is always the current hour and the 30 minute
// is always the nearest 30 minute that is the present
//
// The most laborious invocation appears to be our best friend here.
// That's this one, from mdn:
//
// new Date(year, month[, day[, hour[, minutes[, seconds[, milliseconds]]]]]);
//
var
  isiDevice = navigator.userAgent.match(/ip(hone|od|ad)/i),
  listenEvent = isiDevice ? 'touchend' : 'click',

  ev = EvDa({
    // find out the local tz offset
    offset: (new Date()).getTimezoneOffset(), 
    start_time: '', 
    end_time: '', 
    duration: 'last_half_hour', 
    email: '', 
    notes: ''
  }),

  markers = time_markers();

ev.after('', function(map) {
  if(map.email && map.station && map.start_time && map.end_time) {
    $(".big-button").removeClass('disabled');
  } else {
    $(".big-button").addClass('disabled');
  }
});

$(function(){

  ev('duration', function(what) {
    ev(markers[what]);
  });

  easy_bind(['email', 'notes', 'station', 'duration', 'start_time', 'end_time']);

  ev({ duration: 'last_half_hour' });

  var what = easy_sync(['email', 'station', 'duration']);

  if(what.station) {
    $("#station-preselect")
      .html("Auto-selected from previous use: <b>" + what.station.toUpperCase() + "</b><br/>")
      .append($("<a>Select a different station</a>").click(station_select))
      .show()

  } else {
    station_select();
  } 

  $(".big-button").click(function(){
    if($(this).hasClass('disabled')) {
      return;
    }
    if(ev('duration') == 'custom') {
      ev('human_time', 'from ' + ev('start_time') + ' to ' + ev('end_time'));
    }

    remote('reminder', ev('')).then(function(res) {
      $("#thanks").slideDown();
    }).fail(function(){
      $("#err").slideDown();
    }).always(function(){
      $('.big-button').slideUp();
    });
  });

});

ev('duration', function(what, meta) {
  if(what == 'custom') {
    $("#custom-time").slideDown();
  } else if (meta.old == 'custom') {
    $("#custom-time").slideUp();
  }
});

