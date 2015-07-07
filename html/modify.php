<?php
include_once('db.php');
if($_SERVER['REQUEST_METHOD'] == 'POST') {
  $res = add_station($_POST);
  header('Location: ' . dirname($_SERVER['REQUEST_URI']) . '/admin.php');
  exit(0);
}

if(!empty($_GET['id'])) {
  $station = get_station(['id' => $_GET['id']]);
  if(!$station) { 
    $station = [];
  }
}
?>
<style>
form { display: inline-block }
form > * { padding: 0.5em }
form > :nth-child(2n) { background: #ccc }
label { width: 10em;display: inline-block;}
</style>
<form method="post">
  <?php
    foreach($schema as $key => $value) {
      if($value == 'TEXT') {
        echo "<div><label for='$key'>$key</label>";
        echo "<input 
          value='" . (isset($station[$key]) ? $station[$key] : '') . "'
          type='text' 
          id='$key' name='$key' />
         </div>";
      }
    }
  ?>
  <input type='submit' value='Add/Modify station'>
</form>


