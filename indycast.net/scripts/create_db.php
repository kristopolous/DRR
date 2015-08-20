#!/usr/bin/php
<?php

include_once(__DIR__ . '/../common.php');

function get_column_list($tbl_name) {
  $res = $db->query('pragma table_info(' . $tbl_name . ')');

  return array_map(function($row) { 
    return $row['name'];
  }, sql_all($res));
}

foreach($schema as $tbl_name => $tbl_schema) {
  $existing_column_names = get_column_list($tbl_name);

  // This means we need to create the table
  if (count($existing_column_names) == 0) {
    $params = implode (',', sql_kv($tbl_schema, '', ''));

    $db->exec('create table ' . $tbl_name . ' (' . $params . ')');
  } else {
    // Otherwise we may need to add columns to the table
    $our_column_names = array_keys($tbl_schema);

    $column_to_add_list = array_diff($our_column_names, $existing_column_names);

    if(count($column_to_add_list)) {
      foreach($column_to_add_list as $column_to_add) {
        $column_to_add_schema = $tbl_schema[$column_to_add];
        $db->exec('alter table ' . $table . ' add column ' . $column_to_add . ' ' . $column_to_add_schema);
      }

      // If we added columns then we need to revisit our pragma
      $existing_column_names = get_column_list($tbl_name);
    }
  }

}



/*


    to_remove = my_set(existing_column_names).difference(my_set(our_column_names))

    if (count($to_remove) > 0) {
      our_schema = ','.join(["%s %s" % (key, klass) for key, klass in schema])
      $our_columns = implode(',', $our_column_names);

      $drop_column_sql = "
      CREATE TEMPORARY TABLE my_backup($our_schema);
      INSERT INTO my_backup SELECT $our_columns FROM $table;
      DROP TABLE $table;
      CREATE TABLE $table($our_schema);
      INSERT INTO $table SELECT $our_columns FROM my_backup;
      DROP TABLE my_backup;
      ";

      for sql_line in drop_column_sql.strip().split('\n'):
        db['c'].execute(sql_line)
    }

 */
