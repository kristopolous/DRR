<?php 
include_once('common.php'); 
$qstr = 'select * from stats';

$ret = [];
$isFirst = true;
$qres = $db->query($qstr);
$final = [];

while($row = prune($qres)) {
  $where = [];
  if(strpos($row['version'], 'v') === 0) {
    $parts = explode('-', $row['version']);
    $number = $parts[0];
    if(count($parts) > 2) {
      $build = $parts[2];
    } else {
      $number = 0;
    }
    $row['version'] = trim("$number.$build", 'v');
    $where[] = "version = '{$row['version']}'";
  } 
  if(strlen($row['uuid']) > 15) {
    $parts = explode('-', $row['uuid']);
    $row['uuid'] = array_pop($parts);
    $where[] = "uuid = '{$row['uuid']}'";
  } else if($row['uuid'] === '0' ) {
    $where[] = "uuid = ''";
  }
  foreach(['disk', 'memory', 'latency'] as $key) {
    if(strlen($row[$key]) > 8) {
      $row[$key] = round($row[$key], 3);
      $where[] = "$key = {$row[$key]}";
    }
  }
  if(count($where) > 0) {
    $sql = "update stats set " . implode(',', $where) . 
     " where id = {$row['id']}";
    $db->query($sql);
    echo ".";
  } else {
    echo '@';
  }
}
//echo json_encode($final);
?>

