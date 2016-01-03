<?  
$ua = strtolower($_SERVER['HTTP_USER_AGENT']);
$device = 'device';

if(strpos($ua, 'curl') !== False) {
  include_once('common.php');
  echo "The current stations are healthy:\n\n";
  foreach(active_stations() as $station) {
    echo ' * http://indycast.net/' . $station['callsign'] . "/\n";
  }
  echo "\nQuery the /help end-point to see\nsupported features on a per-station basis.\n\nThanks for using $ua ;-).\n";
  exit(0);
} else {
  header ('Location: /index'); 
}
