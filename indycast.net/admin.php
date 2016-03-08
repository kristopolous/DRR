<?php include_once('common.php'); ?>
<!doctype html5>
<html><head>
<title>admin | indycast</title>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<style>
  body { margin: 1em 0.5em }
  * { font-family: 'Lora', serif; }
  form { display: inline-block; float: right;margin:0 }
  table { background: black;border-spacing: 1px;margin:1em 0}
  tt { font-family: monospace }
  th { font-size: 0.80em; font-weight: normal }
  td,th { padding: 0.25em 0.5em;border-spacing: 1px;background:white}
</style>
</head><body>[ <a href="/">Home</a> ] 
<?php

if($_SERVER['REQUEST_METHOD'] == 'POST') {
  if(md5($_POST['password']) == '8f39db8041d4edc97fda34345ec429b4') {
    $_SESSION['admin'] = 1;
  } else {
    if(isset($_SESSION['admin'])) {
      unset($_SESSION['admin']);
    }
  }
  sleep(1);
  session_write_close();
  header('location: admin.php');
  exit(0);
}

if (!empty($_SESSION['admin']) && $_SESSION['admin'] == 1) {
?>
<b>Mode: Admin</b><form method=post><input type=hidden name=password value=bogusbogusbogus><button>Logout</button></form>
<?php
} else {
?>
<b>Mode: Read-Only</b> <form method=post>Password: <input type=password name=password></form>
<?
}

echo '<table>';
$res = $db->query('select * from stations');
$isFirst = true;
$ping_total = 0;
$drop_total = 0;

while($row = prune($res)) {
  // omit this from displaying.
  foreach(['lat','long'] as $key) {
    unset($row[$key]);
  } 

  $ping_total += $row['pings'];
  $drop_total += $row['drops'];

  foreach(['last_seen', 'first_seen'] as $key) {
    $row[$key] = array_shift(explode(' ', $row[$key]));
  }
  foreach(['latency', 'disk', 'last_record'] as $key) {
    $row[$key] = '<tt>' . number_format($row[$key], 4) . '</tt>';
  }

  foreach(['description', 'notes'] as $key) {
    if(strlen($row[$key]) > 0) {
      $row[$key] = '<a title="' . $row[$key] . '">...</a>';
    }
  }

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
$now = time();

$uptime = round(100 - (100 * $drop_total / $ping_total), 5);
echo "<p>System-wide uptime: $uptime% | Now: $now</p>";

echo '<table>';
$res = $db->query('select * from reminders');
$isFirst = true;

while($row = prune($res)) {
  if($isFirst) {
    echo '<thead><tr>';
    echo '<th>' . implode('</th><th>', array_keys($row)) . '</th>';
    echo '</thead><tbody>';
    $isFirst = False;
  }


  if (is_read_only()) {
    $row['email'] = '<em>(hidden)</em>';
  }

  $intval = intval($row['end_time']);
  $row['end_time'] = "$intval<br><small>(" . ($now - $intval) . ')</small>';
  echo '<tr><td>' . implode('</td><td>', array_values($row)) . '</td>';
  echo '<td>';
  echo '</tr>';
}

?>
</tbody>
</table>
</body></html>
