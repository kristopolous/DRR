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

$height = 1715;
$width = 1715;
$image = new Imagick('../images/radio-backdrop_1715.png');

$draw = new ImagickDraw();

$draw->setStrokeAntialias(true);  //try with and without
$draw->setTextAntialias(true);  //try with and without

$draw = new ImagickDraw();
$draw->setFillColor('#fff');

/* Font properties */
$draw->setFont('DejaVu-Sans-Bold');
$wordList = explode(' ', $show);
$maxLength = 0;

foreach ($wordList as $word) {
  $maxLength = max(strlen($word), $maxLength);
}

$fontsize = 410;
if($maxLength > 6) {
  $fontsize = (6 / $maxLength) * $fontsize;
}

$draw->setFontSize( $fontsize );

$draw->setStrokeColor('#000');
$draw->setStrokeWidth(6);
$draw->setStrokeAntialias(true);  //try with and without
$draw->setTextAntialias(true);  //try with and without
$draw->setGravity(imagick::GRAVITY_NORTH);
//$outputImage->resizeImage(300,0, imagick::FILTER_CATROM, 0.9, false);



$map = 'abcdefghijklmnopqrstuvwxyz';

$parts = strtolower(substr($show, 0, 2));

$offset = strpos($map, $parts[0]) * 26 + strpos($map, $parts[1]);
$hue = floor($offset / (26 * 26) * 360);

$color = new ImagickPixel("hsl($hue, 150, 110)");
$image->colorizeImage($color, 1);

$image->annotateImage($draw, 5, 45, 2, $show);
//$image->thumbnailImage(100, 0);

$image->thumbnailImage($out_res, 0);
// I use curl to debug ... when I do that I don't want the image to come back
if(! preg_match('/curl/', $_SERVER['HTTP_USER_AGENT'])) {
  echo $image;
}

