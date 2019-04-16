<?php
require 'vendor/autoload.php';

use Rhumsaa\Uuid\Uuid;
use Rhumsaa\Uuid\Exception\UnsatisfiedDependencyException;

session_start();
$db = new SQLite3(__DIR__ . "/../db/main.db");

function db_connect() {
  global $db;
  return $db;
}

$schema = [
  'stations' => [
    'id'          => 'INTEGER PRIMARY KEY', 
    
    // FCC callsign or some other unique reference
    'callsign'    => 'TEXT',

    'frequency'   => 'TEXT',
    'description' => 'TEXT',
    'base_url'    => 'TEXT',
    'website'     => 'TEXT',
    'last_seen'   => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'first_seen'  => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'pings'       => 'INTEGER DEFAULT 0',
    'drops'       => 'INTEGER DEFAULT 0',
    'latency'     => 'INTEGER DEFAULT 0',
    'active'      => 'INTEGER DEFAULT 1',

    // Where the station is
    'lat'         => 'DOUBLE default 0',
    'long'        => 'DOUBLE default 0',

    'notes'       => 'TEXT',
    'disk'        => 'DOUBLE default 0',
    'last_record' => 'DOUBLE default 0',
    'load'        => 'DOUBLE default 0',
    'hits'        => 'INTEGER default 0'
  ],

  //
  // The stats table tries to track the long-term
  // run-time, memory, and disk usage of various stations.
  //
  // Especially with respect to their particular versions.
  // Every time a server is started it generates itself a 
  // new UUID which permits for the tracking.
  //
  'stats' => [
    'id'          => 'INTEGER PRIMARY KEY', 
    'callsign'    => 'TEXT',
    'uuid'        => 'TEXT',
    'version'     => 'TEXT',
    'memory'      => 'DOUBLE default 0',
    'disk'        => 'DOUBLE default 0',
    'threadcount' => 'INTEGER default 0',
    'uptime'      => 'INTEGER default 0',
    'latency'     => 'DOUBLE default 0',
    'load'        => 'DOUBLE default 0',
    'now'         => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'hits'        => 'INTEGER default 0'
  ],

  'schedule' => [
    'id'          => 'INTEGER PRIMARY KEY', 
    'callsign'    => 'TEXT',

    'duration'    => 'INTEGER DEFAULT 0',
    'start_min'   => 'INTEGER DEFAULT 0',

    'created_at'  => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'last_seen'   => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',

    'name'        => 'TEXT'
  ],

  // The reminders table is to email someone
  // when they set a reminder for a particular station.
  'reminders' => [
    'id'          => 'INTEGER PRIMARY KEY', 

    'start_time'  => 'TIMESTAMP',
    'end_time'    => 'TIMESTAMP',

    // The human specifies the time in a term such as
    // "current half hour" or someo other way.
    'human_time'  => 'TEXT',

    // This is the TZ offset in minutes, as reported
    // by the browsers' JS engine in order to make sure
    // that emails are sent out reflecting the right 
    // offset time.
    'offset'      => 'INTEGER DEFAULT 0',

    'station'     => 'TEXT',
    'email'       => 'TEXT',

    'notes'       => 'TEXT'
  ],

  'subscriptions' => [
    'id'          => 'INTEGER PRIMARY KEY', 

    // when the person signed up
    'created_at'  => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',

    // times the email was sent
    'sent'        => 'INTEGER DEFAULT 0',

    // last time this particular email was sent
    'last_sent'   => 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',

    'email'       => 'TEXT',
    'station'     => 'TEXT',
    'duration'    => 'INTEGER DEFAULT 0',
    'start_min'   => 'INTEGER DEFAULT 0',

    // The group_id is something that conveniently avoids
    // normalization ... if a show is on multiple times a week
    // and it's part of the same "subscription package" then
    // that is indicated with a groupid so that if a person
    // "unsubscribes" they unsubscribe from the who package
    // and not just a certain day.
    'group_id'     => 'TEXT'
  ]
];

define('INT',       0x0001);
define('STR',       0x0002);
define('SET',       0x0100);
define('REQUIRED',  0x1000);

// sanitize raw input to be friendly towards the database.
// no bobby tables here, no sir.
function sanitize_single($val, $type) {
  $base = SQLite3::escapeString($val);

  if($type & STR) {
    return '"' . $base . '"';
  } else {
    return $base;
  } 
}

function get_column_list($table_name) {
  $db = db_connect();
  $res = $db->query("pragma table_info( $table_name )");

  return array_map(function($row) { 
    return $row['name'];
  }, sql_all($res));
}

function sanitize($list) {
  $ret = [];

  foreach($list as $key => $type) {
    if(isset($_REQUEST[$key])) {
      // if there are multiple values to pull out, then
      // we leverage the sanitize single and make sure we do
      // them one at a time.
      if($type & SET) {
        $ret[$key] = [];

        foreach($_REQUEST[$key] as $el) {
          $ret[$key][] = sanitize_single($el, $type);
        }
      } else {
        // otherwise we can safely pass everything through
        $ret[$key] = sanitize_single($_REQUEST[$key], $type);
      }

    } else {
      $ret[$key] = false;
    }
  }

  return $ret;
}

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

function uuid_gen() {
  return Uuid::uuid4();
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

function sql_all($sql_res) {
  $res = [];
  while( ($res[] = $sql_res->fetchArray(SQLITE3_ASSOC)) );
  array_pop($res);
  return $res;
}

function sql_escape_hash($obj) {
  $res = [];
  foreach($obj as $key => $value) {
    $res[SQLite3::escapeString($key)] = SQLite3::escapeString($value);
  }
  return $res;
}

function sql_kv($hash, $operator = '=', $quotes = "'", $intList = []) {
  $ret = [];
  foreach($hash as $key => $value) {
    if ( is_string($value) ) {
      if(in_array($key, $intList)) {
      	$ret[] = "$key $operator $value";
      } else {
        $ret[] = "$key $operator $quotes$value$quotes";
      }
    }
  } 
  return $ret;
}

function emit_active_stations(){
  foreach(active_stations() as $station) {
    echo '<li><a freq="' . $station['frequency'] . '" desc="' . $station['description'] . '" class="button">' . ($station['callsign']) . '</a></li>';
  }
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

function db_insert($table, $map) {
  $lhs = array_keys($map); $rhs = array_values($map);
  return $db->exec('insert into ' . $table . ' (' . implode(',', $lhs) . ') values (' . implode(',', $rhs) . ')');
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
    return $db->exec('insert into stations (' . implode(',', $lhs) . ') values ("' . implode('","', $rhs) . '")');
  } else {
    $inj = sql_kv($dirty, '=', "'", ['active']);
    $query = 'update stations set ' . implode(',', $inj) . ' where id = ' . $station['id'];
    return $db->exec($query);
  }
}

// Return all the call-signs ordered by the long/lat using a simple 
// euclidean distance
function order_stations_by_distance($long, $lat) {
}

// Looks for a user based on their ip address and the geoip lookup database,
// returning their longitude and latitude
function where_am_i() {
  $addr = $_SERVER['REMOTE_ADDR'];
  if ($addr == '127.0.0.1') { 
    // we'll just use this for testing... it was taken from a coffee shop
    // in "UNINCORPORATED LOS ANGELES" --- also known as Palms.
    $addr = '50.1.134.134';
  }
  $addr = escapeshellarg($addr);

  $res = shell_exec ("/usr/bin/geoiplookup -f scripts/GeoLiteCity.dat $addr");
  $parts = explode(',', $res);
  
  // This means we failed to find it
  if (trim($parts[2]) == 'N/A') {
    // return a null type
    return Null;
  }

  // Otherwise we have a fairly decent regional 
  // idea of where this person is.
  return [$parts[5], $parts[6]];
}

