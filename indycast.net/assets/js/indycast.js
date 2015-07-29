
var 
  // #57 - see why ipad needs to double click
  isiDevice = navigator.userAgent.match(/ip(hone|od|ad)/i),
  listenEvent = isiDevice ? 'touchend' : 'click',
  ev = EvDa({start: '', name: '', station: '', ampm: '', day: []}),
  fullName = {
    sun: 'Sundays', mon: 'Mondays', tue: 'Tuesdays', wed: 'Wednesdays',
    thu: 'Thursdays', fri: 'Fridays', sat: 'Saturdays'
  },
  tpl = {},
  time_re = /^\s*(1[0-2]|[1-9])(:[0-5][0-9])?\s*([ap]m)?\s*$/i;


ev('ampm', function(val){
  if(val) {
    $("#start").val($("#start").val().replace(/\s*([ap]m)\s*/i, val))
  }
});

ev('', function(map) {
  var start_time;

  for(var key in map) {
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

  if(map.station && map.ampm && map.day && map.day.length && map.start && map.duration) {
    if (!map.name) {
      map.name = 'stream';
    }

    map.station = map.station.toLowerCase();

    // #27: dump the spaces, make it lower case and avoid a double am/pm
    start_time = map.start.replace(/\s+/,'').toLowerCase().replace(/[ap]m/, '') + map.ampm;

    url = 'http://' + [
      'indycast.net',
      map.station,
      map.day.join(',') + " ",
      start_time,
      map.duration,
      encodeURI(map.name).replace(/%20/g,'_')
    ].join('/') + ".xml";

    var parts = url.split(' '), 
      single = url.replace(/\s/,''), 
      fullday;
      _map = _.map(map.day, function(what) { return fullName[what] });

    if(map.day.length == 1) {
      fullday = _map[0];
    } else {
      fullday = _map.slice(0, -1).join(', ') + ' and ' + _.last(_map);
    }

    $("#podcast-url").attr({'href': single }).html(
      tpl.podcast({
        name: (map.name || ''),
        day: fullday,
        time: start_time,
        station: map.station.toUpperCase(),
        single: single,
        parts: parts
      })
    );

    $("#podcast-notdone").hide();
    $("#podcast-done").show();
  } else {
    $("#podcast-url").html("Please select options above");
    $("#podcast-notdone").show();
    $("#podcast-done").hide();
  }

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

function htmldo(what) {
  // hyperlinking
  what = what.replace(/[a-z]+:\/\/[^\s^<]+/g, '<a href="$&" target=_blank>$&</a>');

  // paragrapherizing
  what = what.replace(/\n/g, '</p><p>');

  // finalerizing
  return '<p>' + what + '</p>';
}

$(function() {
  tpl.podcast = _.template($("#tpl-podcast").html());

  $(".radio-group a").hover(function(){
    $("#description").html("<h2>" + this.innerHTML + "</h2>" + htmldo(this.getAttribute('desc'))).show();
  });

  if(isiDevice) {
    $("#podcast-url").on(listenEvent, function(){
      // why why why ipad...
      document.location = this.getAttribute('href');
    });
  }

  $("#station-query").on('keyup', function(){
    var query = this.value, show_count = [];
    
    $("#station li").each(function(){
      var to_test = this.firstChild.innerHTML;
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

  $("#start,#name").bind('blur focus change keyup',function(){
    ev(this.id, this.value, {node: this});
  });
  
  for(var el in {start:1,name:1}) {
    var $node = $("#" + el),
        val = $node.val();

    if(val) {
      ev(el, val, {node: $node.get(0)});
    }
  }
  
  ev.fire(['start','name']);

});

// #30: Da Goog!
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','//www.google-analytics.com/analytics.js','ga');

ga('create', 'UA-28399789-2', 'auto');
ga('send', 'pageview');
