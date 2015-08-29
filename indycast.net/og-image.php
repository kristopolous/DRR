<?php
if(preg_match('/reddit/i', $_SERVER['HTTP_USER_AGENT'])) {
  header('Location: images/square-indycast_70.png');
} else {
  header('Location: images/fb-image.png');
}
