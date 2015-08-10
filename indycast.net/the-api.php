<?php
include_once('common.php');

$request = $_GET['func'];

if($request == 'stations') {
  echo json_encode(active_stations());
} else {
  echo json_encode(['error' => 'uknown api call']);
}
