<?php

$callsign = $_GET['callsign'];

$file = "../../server/configs/$callsign.txt";
if(file_exists($file)) {
  $config = file_get_contents($file);
  preg_match_all('/stream=(.*)\n/m', $config, $matches);
  if(count($matches) == 2) {
    echo $matches[1][0];
  }
}
