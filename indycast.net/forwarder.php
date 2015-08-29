<?php
include_once('common.php');
$parts = explode('/', $_SERVER['QUERY_STRING']);
$callsign = array_shift($parts);
$request = implode('/', $parts);
$station = get_station(['callsign' => $callsign]);

if($station) {
  // Don't redirect unless needed
  $url = 'http://' . $station['base_url'] . '/' . implode("/", array_map("rawurlencode", explode("/", $request)));

  if (
    strpos($request, '.xml') !== false || 
    strpos($request, '.pls') !== false || 
    strpos($request, '.m3u') !== false || 
    array_search($request, ['my_uuid', 'heartbeat', 'help', 'stats']) !== false
  ) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
    $data = curl_exec($ch);
    $info = curl_getinfo($ch);
    header('Content-Type: ' . $info['content_type']);
    header('X-Forwarded-URL: ' . $url);

    echo $data;

  } else {
    header('Location: ' . $url);
  }
}
