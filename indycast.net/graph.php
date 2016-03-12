<?php 
include_once('common.php'); 

$vars = sanitize($_GET);
$where = [];
if($station = @$vars['station']) {
  $where[] = "callsign = '$station'";
}
if($start = @$vars['start']) {
  $where[] = "now > $start";
}
if($end = @$vars['end']) {
  $where[] = "now < $end";
}

$qstr = 'select * from stats';
if(count($where) > 0) {
  $qstr .= " where " . implode(' and ', $where);
}

$ret = [];
$qres = $db->query($qstr);
while($row = prune($qres)) {
  $ret[] = $row;
}

if($var = @$_GET['var']) {
  echo "var $var = ";
}
echo json_encode($ret);
?>

