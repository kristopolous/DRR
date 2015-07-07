<?php
include_once('db.php');

$res = $db->exec('select * from stations');

var_dump($res);

?>
