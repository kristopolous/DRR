<?php
include_once('common.php');

$params = implode (',', sql_kv($schema, '', ''));

$db->exec('create table stations(' . $params . ')');

