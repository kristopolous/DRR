
var 
  // #57 - see why ipad needs to double click
  isiDevice = navigator.userAgent.match(/ip(hone|od|ad)/i),
  isMobile = true,
  listenEvent = isiDevice ? 'touchend' : 'click',
  ev = EvDa({start: '', name: '', station: '', ampm: '', day: []}),
  fullName = {
    sun: 'Sundays', mon: 'Mondays', tue: 'Tuesdays', wed: 'Wednesdays',
    thu: 'Thursdays', fri: 'Fridays', sat: 'Saturdays'
  },
  tpl = {},
  time_re = /^\s*(1[0-2]|[1-9])(:[0-5][0-9])?\s*([ap]m)?\s*$/i;

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
  
// #30: Da Goog!
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','//www.google-analytics.com/analytics.js','ga');

ga('create', 'UA-28399789-2', 'auto');
ga('send', 'pageview');
