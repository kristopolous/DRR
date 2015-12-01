<?php
include_once('common.php');

if($_SERVER['REQUEST_METHOD'] == 'POST') {
  $res = add_station($_POST);

  $dir = dirname($_SERVER['REQUEST_URI']);

  if (!empty($dir) && strlen($dir) > 2) {
    $dir .= '/';
  } else {
    $dir = 'http://indycast.net/';
  }

  header('Location: /admin.php');
  exit(0);
}

$station = false;
if(!empty($_GET['id'])) {
  $station = get_station(['id' => $_GET['id']]);
}

if (!$station) { 
  $station = [];
  echo '<title>new station | indycast</title>';
} else {
  echo '<title>' . $station['callsign'] . ' modify | indycast</title>';
}

?>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<style>
  body { margin: 2em }
  * { font-family: 'Lora', serif; }
form { display: inline-block }
form > * { padding: 0.5em }
form > :nth-child(2n) { background: #ddd }
label { width: 10em;display: inline-block;}
button { padding: 0}
</style>
<form method="post">
  <?php
    foreach($schema['stations'] as $key => $value) {
      if($value == 'TEXT' || array_search($key, ['active', 'lat', 'long']) !== false) {
        echo "<div><label for='$key'>$key</label>";
        if($key == 'active') {
          echo '<input type="radio" name="active" value="1" ' . ($station[$key] == '1' ? 'checked' : '') . '>yes';
          echo '<input type="radio" name="active" value="0" ' . ($station[$key] == '0' ? 'checked' : '') . '>no';
          echo '</div>';
        } else if($key == 'description') {
          echo "<textarea
            rows='5'
            cols='60'
            type='text' 
            id='$key' name='$key' />" . (isset($station[$key]) ? $station[$key] : '') . "</textarea>
           </div>";
        } else {
          echo "<input 
            value='" . (isset($station[$key]) ? $station[$key] : '') . "'
            type='text' 
            id='$key' name='$key' />
           </div>";
        }
      }
    }
  ?>
  <input type='submit' value='Add/Modify station'>
  <a href="admin.php">cancel</a>
</form>
