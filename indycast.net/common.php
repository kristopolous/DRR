<?
session_start();
$db = new SQLite3("../db/main.db");

$schema = [
  'id'          => 'INTEGER PRIMARY KEY', 
  
  // FCC callsign or some other unique reference
  'callsign'    => 'TEXT',

  // an integer in megahertz * 100, such as 8990 or 9070 ... this matches the port usually.
  'frequenty'   => 'INTEGER DEFAULT 0',
  'description' => 'TEXT',
  'base_url'    => 'TEXT',
  'last_seen'   => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
  'first_seen'  => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
  'pings'       => 'INTEGER DEFAULT 0',
  'drops'       => 'INTEGER DEFAULT 0',
  'latency'     => 'INTEGER DEFAULT 0',
  'active'      => 'INTEGER DEFAULT 1',

  // Where the station is
  'lat'         => 'DOUBLE default 0',
  'long'        => 'DOUBLE default 0',

  'log'         => 'TEXT',
  'notes'       => 'TEXT'
];

function is_read_only() {
  return empty($_SESSION['admin']) || $_SESSION['admin'] != 1;
}

function db_all($what) {
  $res = [];
  while($item = prune($what)) {
    $res[] = $item;
  }
  return $res;
}

function db_get($str) {
  global $db;
  $res = $db->query($str);
  if($res) {
    return $res->fetchArray();
  }
}


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

function sql_kv($hash, $operator = '=', $quotes = "'") {
  $ret = [];
  foreach($hash as $key => $value) {
    if ( !empty($value) ) {
      $ret[] = "$key $operator $quotes$value$quotes";
    }
  } 
  return $ret;
}

// active stations are things we've seen in the past few days
function active_stations() {
  global $db;
  return db_all($db->query('select * from stations where active = 1 order by callsign asc'));
}

function get_station($dirty) {
  $clean = sql_escape_hash($dirty);
  $inj = sql_kv($clean);
  return db_get('select * from stations where ' . implode(' and ', $inj));
}

function del_station($dirty) {
  if (is_read_only()) {
    return false;
  }

  global $db;
  $clean = sql_escape_hash($dirty);
  $inj = sql_kv($dirty);
  return $db->exec('update stations set active = 0 where ' . implode(' and ', $inj));
}

function add_station($dirty) {
  if (is_read_only()) {
    return false;
  }

  global $db;
  $clean = sql_escape_hash($dirty);

  $station = db_get('select * from stations where callsign = "' . $clean['callsign'] . '"');
  if(!$station) {
    $lhs = array_keys($dirty); $rhs = array_values($dirty);
    return $db->exec('insert into stations (' . implode(',', $lhs) . ') values ("' . implode('","', $dirty) . '")');
  } else {
    $inj = sql_kv($dirty);
    return $db->exec('update stations set ' . implode(',', $inj) . ' where id = ' . $station['id']);
  }
}

// Return all the call-signs ordered by the long/lat using a simple 
// euclidean distance
function order_stations_by_distance($long, $lat) {
}

// Looks for a user based on their ip address and the geoip lookup database,
// returning their longitude and latitude
function where_am_i() {
}

