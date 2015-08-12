#!/usr/bin/php
<?php

include_once(__DIR__ . '/../common.php');

foreach($schema as $tbl_name => $tbl_schema) {
  $params = implode (',', sql_kv($tbl_schema, '', ''));

  $db->exec('create table ' . $tbl_name . ' (' . $params . ')');
}

