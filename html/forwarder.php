<?php
include_once('db.php');
$parts = explode('/', $_SERVER['QUERY_STRING']);
$callsign = array_shift($parts);
$request = implode('/', $parts);
$station = get_station(['callsign' => $callsign]);

if($station) {
  echo file_get_contents('http://' . $station['base_url'] . '/' . $request);
}
