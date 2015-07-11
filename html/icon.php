<?php

header('Content-type: image/png');

$height = 1715;
$width = 1715;

$show = $_GET['show'];
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

$fontsize = 420;
if($maxLength > 6) {
  $fontsize = (6 / $maxLength) * $fontsize;
}

$draw->setFontSize( $fontsize );

$draw->setStrokeColor('#000');
$draw->setStrokeWidth(4);
$draw->setStrokeAntialias(true);  //try with and without
$draw->setTextAntialias(true);  //try with and without
$draw->setGravity(imagick::GRAVITY_SOUTH);
$outputImage = new Imagick();
$outputImage->newImage($height, $width, "transparent");  //transparent canvas
$outputImage->annotateImage($draw, 0, 0, 0, $show);
$outputImage->trimImage(0); //Cut off transparent border
//$outputImage->resizeImage(300,0, imagick::FILTER_CATROM, 0.9, false);


$image = new Imagick('images/radio-backdrop_1715.png');

$map = 'abcdefghijklmnopqrstuvwxyz';

$parts = strtolower(substr($show, 0, 2));

$offset = strpos($map, $parts[0]) * 26 + strpos($map, $parts[1]);
$hue = floor($offset / (26 * 26) * 360);

$color = new ImagickPixel("hsl($hue, 150, 110)");
$image->colorizeImage($color, 1);

//$image->compositeImage($outputImage, imagick::COLOR_ALPHA, 0, 0);
// If 0 is provided as a width or height parameter,
// aspect ratio is maintained
//$image->annotateImage($draw, 10, 45, 0, $show);
//$image->thumbnailImage(100, 0);

// I use curl to debug ... when I do that I don't want the image to come back
if(! preg_match('/curl/', $_SERVER['HTTP_USER_AGENT'])) {
  echo $image;
}

