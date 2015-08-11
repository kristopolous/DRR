<?php
include_once('common.php');

function pl_reminder($what) {
  $param_map = sanitize(
    ['start_time', 'end_time', 'email', 'notes', 'callsign']
  );

  $lhs = array_keys($dirty); $rhs = array_values($dirty);
  if(array_search(false, $rhs, true) !== false) {
    return false;
  }

  return $db->exec('insert into reminders (' . implode(',', $lhs) . ') values ("' . implode('","', $rhs) . '")');
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
