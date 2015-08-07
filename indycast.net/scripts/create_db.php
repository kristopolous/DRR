#!/usr/bin/php

include_once('../common.php');

foreach($schema as list($tbl_name, $tbl_schema)) {
  $params = implode (',', sql_kv($tbl_schema, '', ''));

  $db->exec('create table ' . $tbl_name . ' (' . $params . ')');
}

