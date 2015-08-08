for (my $hour = 1; $hour < 24; $hour++) { 
  for (my $minute = 0; $minute < 60; $minute ++) {
    print "echo :";
    if ($minute == 0) {
      print $hour, ' ';
    } elsif ($minute < 10) {
      $my_minute = '0' . $minute;
      print $hour, ' O', $minute;
    } else {
      $my_minute = $minute;
      print $hour, ' ', $minute;
    }
    print " | text2wav -o " . $hour . $my_minute . ".wav\n";
  }
}
