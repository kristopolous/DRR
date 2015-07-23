<?php
include_once('db.php');

$params = implode (',', sql_kv($schema, '', ''));

$db->exec('create table stations(' . $params . ')');

