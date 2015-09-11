
var 
  // #57 - see why ipad needs to double click
  isiDevice = navigator.userAgent.match(/ip(hone|od|ad)/i),
  html5_audio,
  isMobile = true,
  listenEvent = isiDevice ? 'touchend' : 'click',
  ev = EvDa({start: '', name: '', station: '', ampm: '', day: []}),
  fullName = {
    sun: 'Sundays', mon: 'Mondays', tue: 'Tuesdays', wed: 'Wednesdays',
    thu: 'Thursdays', fri: 'Fridays', sat: 'Saturdays'
  },
  tpl = {},
  time_re = /^\s*(1[0-2]|[1-9])(:[0-5][0-9])?\s*([ap]m)?\s*$/i;

// remote API
// first we have a generic promise harness
function stub() {
  var res = {};

  // Take the things to be stubbed out
  _.each(_.toArray(arguments), function(what) {

    // Assign each one to the map as a function
    res[what] = function(cb) {

      // If the arguments passed in is another function
      // then we put this in our callback list.
      if(_.isFunction(cb)) {
        res[what].cb.push(cb);

        // and return our primary object 
        // for chaining
        return res;

      } else {
        // If the arguments passed in is not a function,
        // then this is data.  We go through the list
        // that we've constructed (if any) and call each
        // callback with the argument passed in - returning
        // the results as a list, if needed.
        return _.map(res[what].cb, function(cb_ix) {
          cb_ix(cb);
        });
      }
    }

    res[what].cb = [];

  });

  return res;
}

// Then we have a queue-able api call system
function do_remote(ep, what, verb, amd) {
  remote.lock = true;
  if(_.isArray(ep)) {
    ep = ep.join('/');
  }

  $[verb || 'post']('/api/' + ep, what, function(res) {
    if(res.result) {
      amd.then(res.data);
    } else {
      amd.fail(res);
    }
  }, 'json')
    .fail(amd.fail)
    .always(function(){
      remote.ix++;
      console.log('r:' + ep + (what === undefined ? "" : (":" + JSON.stringify(what))));
      remote.lock = false;
      amd.always();

      if(remote.queue.length) {
        var opts = remote.queue.shift();
        do_remote.apply(this, opts);
      }
    })
}

function remote_queue(ep, what, verb) {
  var amd = stub('then', 'fail', 'always');

  if(remote.lock) {
    remote.queue.push([ep, what, verb, amd]);
  } else { 
    do_remote(ep, what, verb, amd);
  }

  return amd;
}

function remote(ep, what, verb) {
  var amd = stub('then', 'fail', 'always');

  do_remote(ep, what, verb, amd);

  return amd;
}

remote.queue = [];
remote.lock = false;
remote.ix = 0;

// local storage
function ls(key, value) {
  if (arguments.length == 1) {
    return localStorage[key] || false;
  } else {
    localStorage[key] = value;
  }
  return value;
}

function easy_bind(list, instance) {
  if(!instance) {
    instance = ev;
  }

  _.each(list, function(what) {

    var node = document.querySelector('#' + what);

    if(!node) {
      node = document.querySelector('input[name="' + what + '"]');
      if(!node) {
        throw new Error("Can't find anything matching " + what);
      }
    }

    if(node.nodeName == 'INPUT') {

      $(node).on('blur focus change keyup', function() {
        instance(what, this.value, {node: this});
      });

      instance(what, function(val){ 
        if(val !== undefined) {
          node.value = val; 
        }
      });

    } else {
      $("a,button", node).on(listenEvent, function(){
        // This tricks stupid iDevices into not fucking around and screwing with the user.
        // (Requiring a user to tap twice to select anything.  WTF apple...)
        var mthis = this;

        setTimeout(function(){
          instance(what, mthis.getAttribute('data') || mthis.innerHTML);
        }, 0);
      });

      instance(what, function(val) {
        $("a", node).removeClass('selected');
        if(val) {
          $("a", node).filter(function(){return this.innerHTML == val}).addClass("selected");
          $("a[data='" + val + "']", node).addClass("selected");
        }
      });
    }

    instance.fire(what); 
  });
}

function time_markers() {
  var right_now = new Date();

  return {
    current_hour: {
      human_time: 'the current hour',
      start_time: +date_diff(right_now, {minutes: 0}) / 1000,
      end_time: +date_diff(right_now, {minutes: 0, hours: "+1"}) / 1000
    },
  
    last_half_hour: {
      human_time: 'the previous half hour',
      start_time: +date_diff(right_now, {minutes: "- 30 - ts.getMinutes() % 30"}) / 1000,
      end_time: +date_diff(right_now, {minutes: "- ts.getMinutes() % 30"}) / 1000
    },

    current_half_hour: {
      human_time: 'the current half hour',
      start_time: +date_diff(right_now, {minutes: " - (ts.getMinutes() % 30)"}) / 1000,
      end_time: +date_diff(right_now, {minutes: " + 30 - (ts.getMinutes() % 30)"}) / 1000
    }
  };
}

function easy_sync(list) {
  _.each(list, function(what) {
    if(ls(what)) {
      ev(what, ls(what));
    } 
    ev.after(what, function(value) {
      ls(what, value);
    });
  });
  return ev('');
}

function station_select() {
  $("#station-preselect").slideUp();
  $("#station").slideDown();
}

function htmldo(what) {
  // hyperlinking
  what = what.replace(/[a-z]+:\/\/[^\s^<]+/g, '<a href="$&" target=_blank>$&</a>');

  // paragrapherizing
  what = what.replace(/\n/g, '</p><p>');

  // finalerizing
  return '<p>' + what + '</p>';
}

//
// This is a python inspired way of doing things.
// change_map has datetime.timedelta syntax and operates
// 
//  as an override if it's an integer
//  as an eval if it's a string (such as +1 or -1)
//
// Currently all we care about are 
// hours and minutes.
//
// seconds and milliseconds are zeroed for us.
//
// It can be empty of course.
//
function date_diff(ts, change_map) {

  change_map = change_map || {};

  if( !('hours' in change_map) ) {
    change_map['hours'] = ts.getHours();
  } else if (change_map.hours.length) {
    // oh noes! The spirit of Douglas Crockford has now cursed my family!
    eval("change_map['hours'] = ts.getHours() " + change_map['hours']);
  }

  if( !('minutes' in change_map) ) {
    change_map['minutes'] = ts.getMinutes();
  } else if (change_map.minutes.length) {
    eval("change_map['minutes'] = ts.getMinutes() " + change_map['minutes']);
  }
  console.log(change_map);

  return new Date(
    ts.getFullYear(),
    ts.getMonth(),
    ts.getDate(),
    change_map.hours,
    change_map.minutes,
    0,
    0
  );
}

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
  if(!html5_audio) {
    html5_audio = document.getElementById('radio-control');
  }

  var local = self.audio_count ? self.audio_count : 0;

  $("#url").html(url);

  $("#flash-widget").hide();
  html5_audio.addEventListener('error', function() {
    $("#html5-widget").hide();
    set_fallback(url, local);
  });

  html5_audio.addEventListener('loadstart', function(){
    $("#html5-widget").show();
  });

  html5_audio.src = url;

  if(self.hasOwnProperty('audio_count')) {
    // Don't auto-play if it's the first
    if (audio_count > 0) {
      html5_audio.play();
    }

    audio_count ++;
  }

  return url;
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

$(function() {
  $("#template-list > script").each(function(){
    var name = this.id.split('-').pop();
    tpl[name] = _.template(this.innerHTML);
  });
});

// #30: Da Goog!
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','//www.google-analytics.com/analytics.js','ga');

ga('create', 'UA-28399789-2', 'auto');
ga('send', 'pageview');

// mixpanel
(function(e,b){if(!b.__SV){var a,f,i,g;window.mixpanel=b;b._i=[];b.init=function(a,e,d){function f(b,h){var a=h.split(".");2==a.length&&(b=b[a[0]],h=a[1]);b[h]=function(){b.push([h].concat(Array.prototype.slice.call(arguments,0)))}}var c=b;"undefined"!==typeof d?c=b[d]=[]:d="mixpanel";c.people=c.people||[];c.toString=function(b){var a="mixpanel";"mixpanel"!==d&&(a+="."+d);b||(a+=" (stub)");return a};c.people.toString=function(){return c.toString(1)+".people (stub)"};i="disable time_event track track_pageview track_links track_forms register register_once alias unregister identify name_tag set_config people.set people.set_once people.increment people.append people.union people.track_charge people.clear_charges people.delete_user".split(" ");
for(g=0;g<i.length;g++)f(c,i[g]);b._i.push([a,e,d])};b.__SV=1.2;a=e.createElement("script");a.type="text/javascript";a.async=!0;a.src="undefined"!==typeof MIXPANEL_CUSTOM_LIB_URL?MIXPANEL_CUSTOM_LIB_URL:"file:"===e.location.protocol&&"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js".match(/^\/\//)?"https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js":"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js";f=e.getElementsByTagName("script")[0];f.parentNode.insertBefore(a,f)}})(document,window.mixpanel||[]);
mixpanel.init("4a4a5eed185198ed77fb5ca1edf90a27");
