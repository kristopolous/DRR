<?php
include_once('db.php');

if($_SERVER['REQUEST_METHOD'] == 'POST') {
  if(isset($_POST['_action'])) {
    unset($_POST['_action']);
    $res = del_station($_POST);
  } else {
    $_POST['active'] = 1;
    $res = add_station($_POST);
  }

  $dir = dirname($_SERVER['REQUEST_URI']);

  if (!empty($dir) && strlen($dir) > 2) {
    $dir .= '/';
  } else {
    $dir = 'http://indycast.net/';
  }

  header('Location: ' . $dir . 'admin.php');
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
    foreach($schema as $key => $value) {
      if($value == 'TEXT') {
        echo "<div><label for='$key'>$key</label>";
        if($key == 'description') {
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
<?php if (!empty($station)) { ?>
<form method="post">
  <input type='hidden' name='id' value='<?= $station['id'] ?>'>
  <input type='hidden' value='delete' name='_action'>
  <button>Delete <?= $station['callsign'] ?></button>
</form>
<?php } ?>
