<?
$db = new SQLite3("main.db");
$read_only = ($_SERVER['REMOTE_ADDR'] !== '::1');
$schema = [
  'id'          => 'INTEGER PRIMARY KEY', 
  'callsign'    => 'TEXT',
  'description' => 'TEXT',
  'base_url'    => 'TEXT',
  'last_seen'   => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
  'first_seen'  => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
  'pings'       => 'INTEGER',
  'drops'       => 'INTEGER',
  'latency'     => 'INTEGER',
  'log'         => 'TEXT',
  'notes'       => 'TEXT'
];

function prune($obj) {
  $ret = $obj->fetchArray();
  if($ret) {
    foreach(array_keys($ret) as $key) {
      if(strval(intval($key)) == $key) {
        unset($ret[$key]);
      }
    }
  } 
  return $ret;
}

function sql_escape_hash($obj) {
  $res = [];
  foreach($obj as $key => $value) {
    $res[SQLite3::escapeString($key)] = SQLite3::escapeString($value);
  }
  return $res;
}

function add_station($dirty) {
  global $db;
  $clean = sql_escape_hash($dirty);

  $db->exec('select * from stations where callsign = "' . $clean['callsign'] . '"');
  var_dump($var);
}

