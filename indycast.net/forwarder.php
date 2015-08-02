<?php
include_once('db.php');
$parts = explode('/', $_SERVER['QUERY_STRING']);
$callsign = array_shift($parts);
$request = implode('/', $parts);
$station = get_station(['callsign' => $callsign]);

if($station) {
//var_dump($_SERVER);
  $url = 'http://' . $station['base_url'] . '/' . implode("/", array_map("rawurlencode", explode("/", $request)));
  header('Location: ' . $url);
  /*
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, $url);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
  $data = curl_exec($ch);
  $info = curl_getinfo($ch);
  header('Content-Type: ' . $info['content_type']);
  echo $data;
   */
}
