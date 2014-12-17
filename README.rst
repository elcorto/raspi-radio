About
-----
A very minimalistic Tkinter GUI for playing web radio streams. Ment to be used
on a Raspberry Pi TFT display (like the `watterott
<https://github.com/watterott/RPi-Display>`_ RPi display or the `adafruit
<http://www.adafruit.com/product/1601>`_ PiTFT display, both 320x240), running
Raspbian and an X server (no SDL/Pygame needed). Tkinter and LXDE on the
Raspbian Pi B+ model don't use much resources, so that's OK.

Streams
-------
There is no connection to icecast servers, so no search by genre etc. Simply
define streams in ``streams.json`` (a playlist), which is a list of
dictionaries::

    [
        {"name": "station1", 
         "url": "http://..."},
        {"name": "station2", 
         "url": "http://..."},
        ...
    ]      
    
We use mplayer for playing streams, so mpd/mpc is not needed. We store the last
played stream in ``last_stream.json`` and automatically start that the next
time. To extract stream URIs from downloaded m3u or pls files, just look into
the files and copy the URIs to ``stream.json`` and define a stream name.

Install
-------
::
    
    [elcorto@kenny ~/.../hg/raspi-radio]$ scp * raspi:raspi-radio/
    pi@raspi ~/raspi-radio $ cp icon-raspi-radio-white.png ~/.icons/
    pi@raspi ~/raspi-radio $ cp raspi-radio.desktop ~/Desktop/
    pi@raspi ~/raspi-radio $ sudo cp 200raspi-radio /etc/X11/Xsession.d/; 
    pi@raspi ~/raspi-radio $ sudo chmod ugo+r /etc/X11/Xsession.d/200raspi-radio

Usage
-----
::

    python player.py

See also ``start.sh`` for how to actually use it.


Thanks
------
Icons are an adapted version of
http://www.flaticon.com/free-icon/volume-bars-player-music_477 (creative
commons license http://creativecommons.org/licenses/by/3.0/legalcode). We added
a white background (the original was transparent).
