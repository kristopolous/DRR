#!/usr/bin/php
<?php

include_once(__DIR__ . '/../common.php');

foreach($schema as $tbl_name => $tbl_schema) {
  $existing_schema = $db->exec('pragma table_info(' . $tbl_name . ')');
  existing_column_names = [str(row[1]) for row in existing_schema]

  $params = implode (',', sql_kv($tbl_schema, '', ''));

  $db->exec('create table ' . $tbl_name . ' (' . $params . ')');
}


    our_column_names = [row[0] for row in schema]

    # print table, existing_column_names, our_column_names

    to_add = my_set(our_column_names).difference(my_set(existing_column_names))

    # These are the things we should add ... this can be an empty set, that's fine.
    for key in to_add:
      # 
      # sqlite doesn't support adding things into positional places (add column after X)
      # they just get tacked on at the end ... which is fine - you'd have to rebuild 
      # everything to achieve positional columns - that's not worth it - we just always 
      # tack on at the end as a policy in our schema and we'll be fine.
      #
      # However, given all of that, we still need the schema
      #
      our_schema = schema[our_column_names.index(key)][1]
      # print 'alter table %s add column %s %s' % (table, key, our_schema)
      db['c'].execute('alter table %s add column %s %s' % (table, key, our_schema))
      db['conn'].commit()

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

