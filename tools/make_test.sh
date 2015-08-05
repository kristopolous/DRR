#!/bin/bash

base_dir=~/radio/test

[ -e $base_dir/rawts ] || mkdir $base_dir/rawts
[ -e $base_dir/rawsec ] || mkdir $base_dir/rawsec
[ -e $base_dir/mints ] || mkdir $base_dir/mints
[ -e $base_dir/fullts ] || mkdir $base_dir/fullts

make_silence() {
  cd $base_dir

  sox -n -r 16000 -c 1 silence.wav trim 0.0 60.0
}

make_seconds() {
  cd $base_dir/rawsec
  ( 
    echo 'set -x'
    cat <<- 'endl' | perl
      for (my $second = 5; $second < 60; $second += 5) { 
        print "echo :", $second, " seconds | text2wave -o " . $second . ".wav\n";
      }
endl
  ) > make_seconds.sh
  sh make_seconds.sh
}

make_minutes() {
  cd $base_dir/rawts

  ( 
    echo 'set -x'
    cat <<- 'endl' | perl
      for (my $hour = 0; $hour < 24; $hour++) { 
        if ($hour < 10 ) {
          $my_hour = '0' . $hour;
        } else {
          $my_hour = $hour;
        }
        for (my $minute = 0; $minute < 60; $minute ++) {
          print "echo :";
          if ($minute == 0) {
            print $hour, " o clock";
            $my_minute = '0' . $minute;
          } elsif ($minute < 10) {
            $my_minute = '0' . $minute;
            print $hour, ' O', $minute;
          } else {
            $my_minute = $minute;
            print $hour, ' ', $minute;
          }
          print " | text2wave -o " . $my_hour . $my_minute . ".wav\n";
        }
      }
endl
  ) > make_minutes.sh

  sh make_minutes.sh
}

append_silence_to_minutes() {

  cd $base_dir/rawts/

  for i in *wav; do
    # Create the over-a-minute version
    [ -e $base_dir/fullts/$i ] || sox $i $base_dir/silence.wav $base_dir/fullts/$i

    # truncate it
    [ -e $base_dir/mints/$i ] || sox $base_dir/fullts/$i $base_dir/mints/$i trim 0.0 60.0
  done
}

make_silence
# make_minutes
make_seconds
#append_silence_to_minutes
