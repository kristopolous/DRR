<?php 
include_once('common.php'); 

$ret = [];
$qres = $db->query('select * from stats');
while($row = prune($qres)) {
  $ret[] = $row;
}
echo json_encode($ret, JSON_PRETTY_PRINT);
?>

