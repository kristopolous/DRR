<?php
include_once('db.php');
if($_SERVER['REQUEST_METHOD'] == 'POST') {
  add_station($_POST);
  exit(0);
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
        echo "<div><label for='$key'>$key</label><input type='text' id='$key' name='$key'></input></div>";
      }
    }
  ?>
  <input type='submit' value='Add station'>
</form>


