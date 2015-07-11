<?php
$show = $_GET['show'];

header('Content-type: image/png');

// TODO: security vuln.
if(file_exists($show)) {
  return file_get_contents($show);  
}

// strip the extension.
$show = preg_replace('/.png$/', '', $show);

// get the resolution.
preg_match('/_(\d*)$/', $show, $matches);
$out_res = 512;

if(count($matches)) {
  $out_res = intval($matches[1]);
  $show = substr($show, 0, strrpos($show, '_'));
} 

// from http://stackoverflow.com/questions/5746537/how-can-i-wrap-text-using-imagick-in-php-so-that-it-is-drawn-as-multiline-text
function wordWrapAnnotation($image, $draw, $text, $maxWidth) {   
  $text = trim($text);

  $words = preg_split('%\s%', $text, -1, PREG_SPLIT_NO_EMPTY);
  $lines = array();
  $i = 0;
  $lineHeight = 0;

  while (count($words) > 0) {   
    $metrics = $image->queryFontMetrics($draw, implode(' ', array_slice($words, 0, ++$i)));
    $lineHeight = max($metrics['textHeight'], $lineHeight);

    // check if we have found the word that exceeds the line width
    if ($metrics['textWidth'] > $maxWidth or count($words) < $i) {   
      // handle case where a single word is longer than the allowed line width (just add this as a word on its own line?)
      if ($i == 1) {
        $i++;
      }

      $lines[] = implode(' ', array_slice($words, 0, --$i));
      $words = array_slice($words, $i);
      $i = 0;
    }   
  }   

  return array($lines, $lineHeight);
}

function get_font_size($phrase) {
  $wordList = explode(' ', $phrase);
  $maxLength = 0;

  foreach ($wordList as $word) {
    $maxLength = max(strlen($word), $maxLength);
  }

  $fontsize = 397;
  if($maxLength > 6) {
    $fontsize = (6 / $maxLength) * $fontsize;
  }
  return max($fontsize, 200);
}

function tint_bg(&$image, $phrase) {
  $map = 'abcdefghijklmnopqrstuvwxyz';

  $parts = strtolower(substr($phrase, 0, 2));

  $offset = strpos($map, $parts[0]) * 26 + strpos($map, $parts[1]);
  $hue = floor($offset / (26 * 26) * 360);

  $strcolor = "hsl($hue, 230, 110)";
  $color = new ImagickPixel($strcolor);
  $image->colorizeImage($color, 1);
  return $hue;
}

$height = 1715;
$width = 1715;
$image = new Imagick('../images/radio-backdrop_1715.png');

$draw = new ImagickDraw();
$hue = tint_bg($image, $show);
$draw->setFont('DejaVu-Sans-Bold');

$draw->setFontSize( get_font_size($show) );
$draw->setStrokeColor("black");
$draw->setFillColor("white");
$draw->setStrokeWidth(6);//max(min(18 * (450 / $out_res), 30), 6));
$draw->setStrokeAntialias(true);
$draw->setTextAntialias(true); 
$draw->setTextAlignment(imagick::ALIGN_LEFT);
$draw->setGravity(imagick::GRAVITY_NORTH);

list($parts, $height) = wordWrapAnnotation($image, $draw, $show, 1635);
$ix = 0;
foreach($parts as $line) {
  $image->annotateImage($draw, 40, ($ix + 1) * $height, 0, $line);
  $ix ++;
}

$image->thumbnailImage($out_res, 0);

// I use curl to debug ... when I do that I don't want the image to come back
if(! preg_match('/curl/', $_SERVER['HTTP_USER_AGENT'])) {
  echo $image;
}

