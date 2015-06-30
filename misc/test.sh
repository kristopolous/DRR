asset=radio-45967.png
width=`identify -format %w $asset`;
echo $width
convert \
  -font Arial \
  -pointsize 420\
  -background '#0006' -fill '#FFFE' -gravity center -size ${width}x1920 \
  caption:"Head space" \
  $asset +swap -gravity south -composite logo_full.png

convert logo_full.png -resize  360x -fill goldenrod -tint 100 logo_360.png
display logo_360.png
