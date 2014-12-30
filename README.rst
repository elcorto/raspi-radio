About
-----
A very minimalistic Tkinter GUI for playing web radio streams. Ment to be used
on a Raspberry Pi touchscreen TFT display (like the `watterott
<https://github.com/watterott/RPi-Display>`_ RPi display or the `adafruit
<http://www.adafruit.com/product/1601>`_ PiTFT display, both 320x240), running
Raspbian and an X server (no SDL/Pygame). Tkinter and LXDE on the
Raspbian Pi B+ model don't use much resources, so that's OK.

Currently, there is no connection to icecast servers, so no search by genre
etc. Also, we use mplayer for playing streams and we therefore don't need mpd
and mpc.


Streams
-------
In the config directory

::
    
    ~/.raspi-radio/

streams are defined in plain text files. We support a custom file format based
on json and m3u playlists.

In case of json (the default, as in ``player.py -f json``), define streams in a
file ``streams.json`` (a playlist), which is a list of dictionaries::

    [
        {"name": "soma 80s", 
         "url":  "http://ice.somafm.com/u80s"},
        {"name": "soma groove", 
         "url":  "http://ice.somafm.com/groovesalad"},
        ...
    ]      
    
We store the last played stream in ``last_stream.json`` and automatically start
that the next time. To extract stream URLs from downloaded m3u or pls files,
just look into the files and copy the URLs to ``streams.json`` and define a
stream name.

You can also use a list of stream URLs in a playlist ``stream.m3u``. For that
to work, use ``M3UPlayer`` instead of ``JsonPlayer`` in ``player.py`` as in::

    ./player.py -f m3u

If a m3u playlist is used, we try to obtain the stream name metadata from
mplayer's output (just like we get the current track title). This leads to
slower startup times on the raspi. First, the tream URL is displayed and some
seconds later the obtained stream name. With json, startup is much faster but
you need to define the stream name yourself at first in ``streams.json``.

Install
-------
Copy all files to the raspi::
    
    [me@mybox ~/.../hg/raspi-radio]$ scp * raspi:raspi-radio/
    [me@mybox ~/.../hg/raspi-radio]$ scp ~/.raspi-radio/streams* raspi:.raspi-radio/

On the raspi, make sure that the radio starts up when X comes up, but not when
we log in via ssh. We use an Xsession startup script::
    
    pi@raspi ~/raspi-radio $ sudo cp 200raspi-radio /etc/X11/Xsession.d/
    pi@raspi ~/raspi-radio $ sudo chmod ugo+r /etc/X11/Xsession.d/200raspi-radio

Install desktop icon if you wish::

    pi@raspi ~/raspi-radio $ cp icon-raspi-radio-white.png ~/.icons/
    pi@raspi ~/raspi-radio $ cp raspi-radio.desktop ~/Desktop/


Usage
-----
::

    python player.py --format json

(the default) or::    
    
    python player.py --format m3u

See also ``player -h`` and ``start.sh`` for how to actually use it.


Thanks
------
Icons are an adapted version of
http://www.flaticon.com/free-icon/volume-bars-player-music_477 (creative
commons license http://creativecommons.org/licenses/by/3.0/legalcode). We added
a white background (the original was transparent).
