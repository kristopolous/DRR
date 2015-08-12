<?php
include_once('common.php');

function pl_reminder($what) {
  $param_map = sanitize(
    ['start_time', 'end_time', 'email', 'notes', 'station']
  );

  foreach(['start_time', 'end_time'] as $date_key) {
    $param_map[$date_key] = strtotime($param_map[$date_key]);

    if(!is_numeric($param_map[$date_key])) {
      return 'false';
    }
  }

  $lhs = array_keys($param_map); $rhs = array_values($param_map);

  if(array_search(false, $rhs, true) !== false) {
    return 'false';
  }

  $db = db_connect();
  $db->exec('insert into reminders (' . implode(',', $lhs) . ') values ("' . implode('","', $rhs) . '")');
  return 'true';
}

function pl_stations() {
  return json_encode(active_stations());
}

if(isset($_REQUEST['func']) && function_exists('pl_' . $_REQUEST['func'])) {
  $toRun = 'pl_' . $_REQUEST['func'];
  unset($_REQUEST['func']);

  $result = $toRun ( $_REQUEST );
  echo $result;
} else {
  echo json_encode(['error' => 'uknown api call']);
}
