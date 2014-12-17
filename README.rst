About
-----
A very minimalistic Tkinter GUI for playing web radio streams. Ment to be used
on a Raspberry Pi TFT display (like the `watterott
<https://github.com/watterott/RPi-Display>`_ RPi display or the `adafruit
<http://www.adafruit.com/product/1601>`_ PiTFT display, both 320x240), running
Raspbian and an X server (no SDL/Pygame needed). Tkinter and LXDE on raspi b+
don't use much resources, so that's OK.

Streams
-------
There is connection to icecast, so no search by genre etc. Simply define
streams in ``streams.json`` (a playlist), which is a list of dictionaries::

    [
        {"name": "station1", 
         "url": "http://..."},
        {"name": "station2", 
         "url": "http://..."},
        ...
    ]      
    
We use mplayer for playing streams,
so mpd/mpc is not needed. We store the last played stream in
``last_stream.json`` and automatically start that the next time. To extract
stream URIs from downloaded m3u or pls files, just look into the files and copy
the URIs to ``stream.json`` and define a stream name.

Install
-------
::
    
    mkdir raspi-radio
    cp /from/somewhere/* raspi-radio/
    cp raspi-radio/icon-raspi-radio-white.png .icons/
    cp raspi-radio/raspi-radio.desktop Desktop/
    cp /from/somewhere/streams.json raspi-radio/

Usage
-----
::

    python player.py

See also ``start.sh`` for how to actually use it.
