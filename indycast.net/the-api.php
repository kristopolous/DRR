<?php
// This is the api entry point for the /api/* calls. It's basically a really
// poor-mans router and controller that doesn't distinguish between HTTP verbs.
include_once('common.php');

function passes($message) {
  return ['result' => true, 'message' => $message];
}

function fails($message) {
  return ['result' => false, 'message' => $message];
}

function pl_subscribe() {
  $p = sanitize([
    'start' => STR,
    'name' => STR,
    'station' => STR,
    'ampm' => STR,
    'day' => STR|SET,
    'duration' => STR,
    'email' => STR
  ]);
  $group_id = uuid_gen();

  $ts_input = [];
  if(is_array($_REQUEST['day'])) {
    foreach($_REQUEST['day'] as $day) {
      $ts_input[] = sprintf("%s %s %s", $day, $_REQUEST['start'], $_REQUEST['duration']);
    }
  } else {
    return fails("Invalid day input");
  }
  $one_line = escapeshellarg(implode('_', $ts_input));

  $to_record_list = json_decode(shell_exec('echo ' . $one_line . ' | ../tools/time_convert.py'), true);

  foreach($to_record_list as $item) {
    $to_insert = [
      'email' => $p['email'],
      'station' => $p['station'],
      'duration' => $item[1],
      'start_min' => $item[0],
      'group_id' => $group_id
    ];
    $res = db_insert('subscriptions', $to_insert);
    var_dump($res);
  }

  var_dump($parts);
  return fails("unimplemented");
}

function pl_unsubscribe() {
  $p = sanitize([
    'email' => STR,
    'groupid' => INT
  ]);

  $who = $p['email'];
  $what = $p['groupid'];

  if(empty($who) || empty($what)) {
    return fails('empty input');
  }

  $db = db_connect();
  // test for existence
  $res = db_get('select * from subscriptions where email="' . $who . '" and groupid="' . $what . '"');

  if(count($res) > 0) {

    $db->exec('delete from subscriptions where email="' . $who . '" and groupid="' . $what . '"');

    return passes('removed ' . count($res) . ' entries');
  } 
  return fails('nothing found');
}

function pl_reminder($what) {

  $param_map = sanitize([
    'start_time' => INT, 
    'end_time' => INT, 
    'email' => STR, 
    'notes' => STR, 
    'station' => STR, 
    'human_time' => STR,
    'offset' => INT
  ]);

  foreach(['start_time', 'end_time'] as $date_key) {
    $value = $param_map[$date_key];

    if(strval(intval($value)) == $value) {
      $param_map[$date_key] = intval($value);
    } else {
      $param_map[$date_key] = strtotime($value);
    }

    if(!is_numeric($param_map[$date_key])) {
      return 'false';
    }
  }

  $lhs = array_keys($param_map); $rhs = array_values($param_map);

  if(array_search(false, $rhs, true) !== false) {
    return 'false';
  }

  $db = db_connect();
  $db->exec('insert into reminders (' . implode(',', $lhs) . ') values (' . implode(',', $rhs) . ')');

  return passes('reminder added');
}

function pl_stations() {
  return json_encode(active_stations());
}

if(isset($_REQUEST['func']) && function_exists('pl_' . $_REQUEST['func'])) {
  $toRun = 'pl_' . $_REQUEST['func'];
  unset($_REQUEST['func']);

  $result = $toRun ( $_REQUEST );
  if(is_string($result)) {
    echo $result;
  } else {
    echo json_encode($result);
  }
} else {
  echo json_encode(fails('uknown api call'));
}
