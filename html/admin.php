<title>admin | indycast</title>
<style>
  table { background: black;border-spacing: 1px}
  td,th { padding: 0.25em;border-spacing: 1px;background:white}
</style>
<table>
<?php
include_once('db.php');

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
  echo '<td><a href="modify.php?id=' . $row['id'] . '">Modify</a></td>';
  echo '</tr>';
}

?>
</tbody>
</table>
<a href="modify.php">Add Station</a>
