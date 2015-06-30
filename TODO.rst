raspi
-----
* screen to laptop (ssh -X) since some apps don't display correctly on the
  rpi-tft -> cannot configure some stuff, also desktop seems to large (taskbar
  is OK, but many icons are not visible)
  => can be done with::

    DISPLAY=:10 <program>
  
  E.g.::
    
    <program> = midori 
  
  (the raspi browser) works, but:: 
    
    <program> = lxpanelctl config
  
  doesn't. And that's what we need!  
    
  The "10" in the display comes from "X11DisplayOffset 10" in
  /etc/ssh/sshd_config.  

player
------
* In fill_queue_playing_stream_metadata(), we constantly keep putting the stream
  metadata into metadata_queue, even if it doesn't change (same track playing).
  In poll_queue_playing_stream_metadata(), we poll that every 2 seconds or so
  but at least we don't update the GUI if the text is the same. But can't we
  just put a new string into metadata_queue if there *is* a new one (e.g. new
  track)? Then we need a push-like mechanism, where we inform
  poll_queue_playing_stream_metadata() of the availability of new metadata.
  This constant put and poll with the queue seems pretty stuipd, even if it
  doesn't cost much. If a push-like mechanism is not possible and we need the
  polling, then at least put nothing in the queue if the metadata doesn't
  change. poll_queue_playing_stream_metadata() sould only do something if there
  is smth new (or anything at all) in metadata_queue.
* Make config file (in ~/.raspi-radio) to read hard-coded mplayer settings like
  cache size etc, or expose a cmd line for that. Or: pass any additional
  options directly to mplayer -- but that means we must know that we use
  mplayer. What do we do in case of mpd being the player? So a config file may
  be better, like so::
    
    [mplayer]
    cache=400

    [mpd]
    ...


playlist
--------
* Find a way to let users modify the playlist ``raspi:.raspi-radio/streams.*``
  from their remote machine. Modify-and-copy via scp is not that much fun. With
  an mpd client, we can modify the currently loaded playlist, e.g. what is in
  mpd's database after ``mpc load <playlist>`` and shown by ``mpc playlist``.
  Can we also modify the to-be-loaded playlist file
  ``.raspi-radio/streams.m3u`` via mpd? That would be good, but I think this is
  not possible. If not, then we need to set up smth like WebDAV (need to help
  Window$ users as well) to establish access to that file.

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
* or it is b/c the stream is aac-plus?
* We also tested mopidy (www.mopidy.com) to replace mpd. mopidy is a music
  player server written in Python. It implements a subset of the mpd protocol.
  We can use any mpd client (like mpc) to run "mpc load/clear/play/stop/...".
  It uses gstreamer for playback. It feels somewhat sluggish compared to the
  original mpd written in C. No extensive tests on the raspi up to now. If we
  install all funny gstreamer plugins "gstreamer1.0-plugins-{good,bad,ugly}"
  then mopidy does also play all streams which we currently use, also fluxfm.

Using mpd (mopidy) over mplayer has some advantages:

* We can steer the playback from any computer / phone with an mpd client.
  See https://docs.mopidy.com/en/latest/clients/mpd/#mpd-clients or
  http://www.musicpd.org/clients/.
  
