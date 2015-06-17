# DRR

Digital **Radio** Recorder

I enjoy listening to some radio programs which I often forget to tune into or are at inappropriate times.

I'd like to record them.  This is the tools I use to do it.

Each station file only has a function named "audio" which describes how the audio is captured.

When they are executed there is 1 argument, the number of hours to record for.  The file is named 
after the script name.

So when I run something like

    kkjz.sh 1

Then I'll get 1 hour audio from that station.

The script will be polling the audio capture system and make sure that it doesn't exit prematurely and if it does, it will start a new session back up
with a different file name.  This means that you may have some gaps in the audio, but at least it will recover from a failure --- a superior method of
course would for the thing to not timeout ... but alas
