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
* JsonPlayer: find smarter way to implement get_selected_stream_metadata(),
  right now we use 
      timeout 5 mplayer --ao=null <stream> | sed ...
  which is pretty brute force. Maybe smth with curl and getting only the stream
  http header?
