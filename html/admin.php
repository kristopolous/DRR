<?php include_once('db.php'); ?>
<!doctype html5>
<html><head>
<title>admin | indycast</title>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<style>
  body { margin: 2em }
  * { font-family: 'Lora', serif; }
  form { display: inline-block; float: right;margin:0 }
  table { background: black;border-spacing: 1px;margin:1em 0}
  td,th { padding: 0.25em 0.5em;border-spacing: 1px;background:white}
</style>
</head><body>
<?php

if($_SERVER['REQUEST_METHOD'] == 'POST') {
  if(md5($_POST['password']) == '8f39db8041d4edc97fda34345ec429b4') {
    $_SESSION['admin'] = 1;
  } else {
    if(isset($_SESSION['admin'])) {
      unset($_SESSION['admin']);
    }
  }
  session_write_close();
  header('location: admin.php');
}

if (!empty($_SESSION['admin']) && $_SESSION['admin'] == 1) {
?>
<b>Mode: Admin</b><form method=post><input type=hidden name=password value=bogusbogusbogus><button>Logout</button></form>
<?
} else {
?>
<b>Mode: Read-Only</b> <form method=post>Password: <input type=password name=password></form>
<?
}

echo '<table>';
$res = $db->query('select * from stations');
$isFirst = true;

while($row = prune($res)) {
  if($isFirst) {
    echo '<thead><tr>';
    echo '<th>' . implode('</th><th>', array_keys($row)) . '</th>';
    echo '</thead><tbody>';
    $isFirst = False;
  }

  echo '<tr><td>' . implode('</td><td>', array_values($row)) . '</td>';
  echo '<td>';
  if (!is_read_only()) {
    echo '<a href="modify.php?id=' . $row['id'] . '">Modify</a></td>';
  } else {
    echo '<em>read-only</em>';
  }
  echo '</tr>';
}

?>
</tbody>
</table>
<?php if (!is_read_only()) { 
  echo '<a href="modify.php">Add Station</a>';
}
?>
</body></html>
