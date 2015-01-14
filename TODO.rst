raspi
-----
* screen to laptop (ssh -X) since some apps don't display correctly on the
  rpi-tft -> cannot configure some stuff, also desktop seems to large (taskbar
  is OK, but many icons are not visible)
  => can be done with 
    DISPLAY=:10 <program>
  E.g. 
    <program> = midori 
  (the raspi browser) works, but 
    <program> = lxpanelctl config
  doesn't. And that's what we need!  
    
  The "10" in the display comes from "X11DisplayOffset 10" in
  /etc/ssh/sshd_config.  

player
------
* Find smarter way to implement get_selected_stream_metadata(),
  for mplayer-based player classes. Right now we use smth like
      ./timeout.sh 5 mplayer --ao=null <stream> | sed ...
  which is pretty brute force. Maybe smth with curl and getting only the stream
  http header?
* We should fetch metadata from the current `playing` stream, not the selected
  one. If we poke around on the touch screen, the selected stream may change,
  and without pressing Play, the playing stream remains the same.

mpd
---
* mpd doesn't play fluxfm (http://fluxfm.de/stream-berlin) currently
* if fluxfm is selected, it stops and automatically starts the next stream
* the error in ~/.mpd/mpd.log is::

    Jan 06 14:58 : client: [367] opened from [::1]:43509
    Jan 06 14:58 : client: [367] closed
    Jan 06 14:58 : client: [368] opened from [::1]:43510
    Jan 06 14:58 : client: [368] closed
    Jan 06 14:58 : output: Failed to open mixer for 'My ALSA Device'
    Jan 06 14:58 : player: played "http://www.fluxfm.de/stream-berlin"
* using pulseaudio instead as backend doesn't work either, the error is gone
  but it still doesn't play and jumps right to the next stream
* may be an alsa <-> pulseaudio conflict since both are installed .. one grabbs
  the stream before the other can .. smth like that
* We also tested mopidy (www.mopidy.com) to replace mpd. mopidy is a music
  player server written in Python. It implements a subset of the mpd protocol.
  We can use any mpd client (like mpc) to run "mpc load/clear/play/stop/...".
  It uses gstreamer for playback. It feels somewhat sluggish compared to the
  original mpd written in C. No extensive tests on the raspi up to now. If we
  install all funny gstreamer plugins "gstreamer1.0-plugins-{good,bad,ugly}"
  then mopidy does also play all streams which we currently use, also fluxfm.

