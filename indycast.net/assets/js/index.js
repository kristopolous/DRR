var _is_ready;

ev('ampm', function(val){
  if(val) {
    $("#start").val($("#start").val().replace(/\s*([ap]m)\s*/i, val))
  }
});

ev('station', function(what) {
  mixpanel.track("station selected");
});

function show_download() {
  console.log(+(new Date()) + "here", _is_ready);

  if(_is_ready) {
    $('#dialog-choose').modal();
  }
}

ev('', function(map) {
  var 
    start_time = "Pick the start time", 
    todo = [],
    tpl_params = {},
    phrase = "Choose the ",
    podcast_url = '',
    live_url = '',
    showname = '',
    single = '',
    parts = [],
    station = "Choose the station", 
    name = '',
    fullday = "Pick the days";

  _is_ready = false;

  for(var key in map) {
    if(!map[key]) {
      continue;
    }

    $("#" + key + " a").removeClass("selected");

    if(key == 'day') {
      _.each(map[key], function(what) {
        $("#" + key + " a:contains(" + what + ")").addClass("selected");
      });
    } else if(key != 'name') {
      $("#" + key + " a:contains(" + map[key] + ")").addClass("selected");
      $("#" + key + " a[data='" + map[key] + "']").addClass("selected");
    }
  }

  if(map.name && map.station && map.ampm && map.day && map.day.length && map.start && map.duration) {
    _is_ready = true;
    phrase = false;

    $("#podcast-done").removeClass('disabled');
  } else {
    $("#podcast-done").addClass('disabled');
    name = "Almost done!";
  }

  if(map.station) {
    station = map.station.toLowerCase();
  } else {
    todo.push('station');
  }

  if(map.day && map.day.length) {
    var _map = _.map(map.day, function(what) { return fullName[what] });
    if(map.day.length == 1) {
      fullday = _map[0];
    } else {
      fullday = _map.slice(0, -1).join(', ') + ' and ' + _.last(_map);
    }
  } else {
    todo.push("day(s) of week");
  }

  if(!map.duration) {
    todo.push('duration');
  }

  // #27: dump the spaces, make it lower case and avoid a double am/pm
  if(map.start) {
    start_time = map.start.replace(/\s+/,'').toLowerCase().replace(/[ap]m/, '') + map.ampm;
  } else {
    todo.push('start time');
  }

  if(map.name) {
    showname = map.name;
  } else {
    todo.push('name');
  }

  if (_is_ready) {
    podcast_url = 'http://' + [
      'indycast.net',
      station,
      map.day.join(','),
      start_time,
      map.duration,
      encodeURI(map.name).replace(/%20/g,'_')
    ].join('/') + ".xml";

    live_url = 'http://' + [
      'indycast.net',
      station,
      'at',
      fullName[map.day[0]].slice(0,-1).toLowerCase() + "_" + start_time,
      map.duration
    ].join('/');

    set_player(live_url);
  } 

  if(todo.length) {
    if(todo.length > 1) {
      phrase += todo.slice(0, -1).join(', ') + ' and ' + todo.slice(-1)[0];
    } else {
      phrase += todo[0];
    }
    phrase += '.';
  } else {
    name = "You're Done.";
    phrase = "Hit the green button.";
  }

  tpl_params = {
    name: name,
    day: fullday,
    time: start_time,
    is_ready: _is_ready,
    showname: showname,
    station: station,
    podcast_url: podcast_url,
    phrase: phrase,
    tweet_text: encodeURI("Listening to a recording of " + station.toUpperCase() + "'s " + showname + " at indycast.net. It's free. You can too: " + live_url),
    live_url: live_url
  };

  _.each(['top','bottom','dialog'], function(what) {
    $("#podcast-" + what).html( tpl[what](tpl_params));
  });

  $("#dialog-title").html('latest episode of ' + showname);

  $("#podcast-container").css({width: $("#podcast-url").width() + 30});
});

ev.test('start', function(v, cb, meta) {
  var res = time_re.test(v);
  
  if(res) {
    if(/[ap]m/.test(v)) {
      ev('ampm', v.slice(-2));
    } 
  } 
   
  $(meta.node)[(res ? 'remove' : 'add') + 'Class']('error');
  cb(res);
});

$(function() {
  $(".radio-group a").hover(function(){
    $("#description").html("<h2>" + this.innerHTML + "</h2>" + htmldo(this.getAttribute('desc'))).show();
  });


  if(isiDevice) {
    $("#podcast-url").on(listenEvent, function(){
      // why why why ipad...
      document.location = this.getAttribute('href');
    });
  }
  $("#podcast-url").click(function(){
    mixpanel.track("podcast-click");
  });

  $("#station-query").on('keyup', function(){
    var query = this.value, show_count = [];
    
    $("#station li").each(function(){
      var to_test = [this.firstChild.innerHTML, this.firstChild.getAttribute('freq')].join(' ');
      if(to_test.search(query) == -1) {
        $(this).hide();
      } else {
        show_count.push(to_test)
        $(this).show();
      }
    });

    if(show_count.length == 1) {
      ev('station', show_count[0]);
    }

  })

  // #23 - multiday recordings
  $("#day a").on(listenEvent, function(){
    ev.setToggle('day', this.innerHTML);
  });

  $(".group a").on(listenEvent, function(){
    var mthis = this;

    // This tricks stupid iDevices into not fucking around and screwing with the user.
    setTimeout(function(){
      var node = $(mthis).parentsUntil("div").last();
      ev(node[0].id, mthis.getAttribute('data') || mthis.innerHTML);
    },0)
  });

  $("#start,#name").bind('change keyup',function(){
    ev(this.id, this.value, {node: this});
  });
  
  for(var el in {start:1, name:1}) {
    var 
      $node = $("#" + el),
      val = $node.val();

    if(val) {
      ev(el, val, {node: $node.get(0)});
    }
  }
  
  ev.fire(['start', 'name']);
});

