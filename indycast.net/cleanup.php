<?php 
include_once('common.php'); 
$qstr = 'select * from stats';

$ret = [];
$isFirst = true;
$qres = $db->query($qstr);
$final = [];
while($row = prune($qres)) {

  foreach(['disk', 'memory', 'latency'] as $key) {
    $row[$key] = round($row[$key], 3);
  }
  $parts = explode('-', $row['version']);
  $number = $parts[0];
  if(count($parts) > 2) {
    $build = $parts[2];
  } else {
    $number = 0;
  }
  $row['version'] = trim("$number.$build", 'v');
  if(strlen($row['uuid'])) {
    $parts = explode('-', $row['uuid']);
    $row['uuid'] = array_pop($parts);
  }
  $final[] = array_values($row);
}
echo json_encode($final);
?>

