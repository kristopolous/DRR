<?php
include_once('db.php');

$read_only = ($_SERVER['REMOTE_ADDR'] !== '::1');

$res = $db->exec('select * from stations');

var_dump($res);

?>
