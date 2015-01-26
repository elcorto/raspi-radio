raspi-radio
===========

About
-----

A very minimalistic Tkinter GUI for playing web radio streams. Ment to be used
on a Raspberry Pi with touchscreen TFT display (like the `watterott
<https://github.com/watterott/RPi-Display>`_ RPi display [that's what we use]
or the `adafruit <http://www.adafruit.com/product/1601>`_ PiTFT display, both
320x240), running Raspbian and an X server (no SDL/Pygame). Tkinter and LXDE on
the Raspberry Pi model B+ don't use much resources, so that's OK.

There is no connection to icecast servers, so no search by genre etc. Also, we
use ``mplayer`` for playing streams and we therefore don't need ``mpd`` and
``mpc`` (but see below).


Streams
-------

In the config directory

::
    
    ~/.raspi-radio/

streams are defined in plain text files. We support a custom file format based
on json and m3u playlists.

In case of json (the default)

::
    
    ./player.py
    ./player.py --format json --player mplayer 

define streams in a file ``streams.json`` (a playlist), which is a list of
dictionaries::

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

You can also use a list of stream URLs in a playlist file ``stream.m3u``::
         
         http://ice.somafm.com/u80s
         http://ice.somafm.com/groovesalad
         ...

Use

::
    
    ./player.py --format m3u

in that case.

If a m3u playlist is used, we try to obtain the stream name metadata from
``mplayer``'s output (just like we get the current track title). This leads to
slower startup times on the raspi. First, the stream URL is displayed and some
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

    ./player.py --format json --player mplayer

(the default) or::    
    
    ./player.py --format m3u --player mplayer
    ./player.py --format m3u --player mpd

See also ``player.py -h`` and ``start.sh`` for how to actually use it.


Thanks
------

Icons are an adapted version of
http://www.flaticon.com/free-icon/volume-bars-player-music_477 (creative
commons license http://creativecommons.org/licenses/by/3.0/legalcode). We added
a white background (the original was transparent).


Raspberry Pi install and setup
==============================

Download Raspbian image from https://github.com/watterott/RPi-Display, then
flash onto the sd card which you will put into the raspi later::
    
    sudo dd if=2014-06-20-wheezy-raspbian-2014-07-25-fbtft-rpi-display-rev2.img of=/dev/mmcblk0

Connect to ethernet, boot and ::

    ssh pi@192.168.1.104

(IP from dhcp, static IP based on MAC address). Run::

    sudo raspi-config

Choose "Enable Boot to Desktop/Scratch" -> "Desktop Log in as user 'pi' at the
graphical desktop". Choose "Expand Filesystem".


Wifi (http://raspberry.eickwinkel.com/wlan.html)::

    [m] /etc/network/interfaces
    auto wlan0
    allow-hotplug wlan0
    iface wlan0 inet dhcp
    wpa-ssid "<wifi router SSID>"
    wpa-psk "<secret wifi key>"


Install (i) some stuff. Purge (p) unused stuff, delete (d) pre-installed stuff::

    [i] install vim mercurial mplayer2 ntp
    [p] wolfram-engine idle idle3 mpd cups-bsd cups-common
        cups-clientcups-bsd cups-common cups-client nfs-common
        debian-reference-common debian-reference-en esound-common nano
        netsurf-gtk netsurf-common samba-common supercollider-server
        supercollider-common supercollider mplayer

    [d] python_games/ Desktop/python-games.desktop Desktop/wolfram*
        Desktop/idle* Desktop/debian-reference-common.desktop

Fix time zone::

    dpkg-reconfigure tz-data

Disable TFT blank
(https://github.com/notro/fbtft-spindle/wiki/FBTFT-image#console)::
    
    [m] etc/kbd/config
    BLANK_TIME=0

Disable screensaver::
    
    For xset(1):
    [i] x11-xserver-utils
    Then:
    [m] /etc/xdg/lxsession/LXDE/autostart
    -   @xscreensaver -no-splash
    +   ##@xscreensaver -no-splash
    +   @xset s noblank
    +   @xset s off
    +   @xset -dpms


mpd / mpc
=========

general info
------------

With MPD (music player daemon), we can have a [radio stream] playlist and
control it with an ``mpd`` client (the most simple one is ``mpc``).

Install the original ``mpd`` server:: 
    
    [i] mpd

or ``mopidy`` (https://docs.mopidy.com/en/latest/installation/debian/#debian-install)::

    wget -q -O - https://apt.mopidy.com/mopidy.gpg | sudo apt-key add -

    [m] /etc/apt/sources.list
    deb http://apt.mopidy.com/ stable main contrib non-free
    deb-src http://apt.mopidy.com/ stable main contrib non-free

    [i] mopidy gstreamer0.10-alsa gstreamer0.10-plugins-ugly
        gstreamer0.10-plugins-bad mpc

For both ``mpd`` and ``mopidy``, we can use the ``mpc`` command line client for testing
stuff.

Usage::

    service mopidy restart # or service mpd restart
    mpc update
    mpc clear
    mpc add http://ice.somafm.com/u80s
    mpc add http://fluxfm.de/stream-berlin
    mpc playlist
    mpc play 1

An m3u playlist is a simple textfile with one stream URL per line. We can feed
that to ``mpd`` by ::
    
    cat streams.m3u | xargs -l mpc add # very slow with mopidy

or copy it to ``/var/lib/mpd/playlists/`` (``/var/lib/mopidy/playlists/`` in
case the ``mpd`` server is ``mopidy`` instead of ``mpd``) and then say::
    
    [mpc update ??]
    mpc load streams

which does ``mpc add`` for each stream. 


run mpd as user process
-----------------------

It is better to set up ``mpd`` as a user process::
    
    sudo apt-get install mpd mpc
    sudo update-rc.d mpd disable
    mkdir ~/.mpd
    touch ~/.mpd/{tag_cache,state,mpd.log,pid}

Copy ``/etc/mpd.conf`` and adapt::
    
    cp /etc/mpd.conf ~/.mpd/
    [m] ~/.mpd/mpf.conf
    playlist_directory      "/home/pi/.raspi-radio"
    db_file                 "/home/pi/.mpd/tag_cache"
    log_file                "/home/pi/.mpd/mpd.log"
    pid_file                "/home/pi/.mpd/pid"
    state_file              "/home/pi/.mpd/state"
    sticker_file            "/home/pi/.mpd/sticker.sql"

The important part is that ``playlist_directory`` is ``/home/pi/.raspi-radio``.
Start the daemon as user ``pi`` (maybe put in some init script)

::

    mpd

and the player by

::

    ./player.py --format m3u --player mpd

We do ``mpc load streams``, which will load the playlist
``~/.raspi-radio/streams.m3u`` into ``mpd``.

why use mpd or mopidy + mpc instead of mplayer, and why not?
------------------------------------------------------------

``mopidy`` is a Python MPD server and much more. It implements a subset of the ``mpd``
protocol. We can use any ``mpd`` client (like ``mpc``) to run ``mpc
load/clear/play/stop/...``. It uses gstreamer for playback. It feels somewhat
sluggish compared to the original ``mpd`` written in C. No extensive tests on the
raspi up to now. If we install all funny gstreamer plugins
"gstreamer1.0-plugins-{good,bad,ugly}" then ``mopidy`` does also play all streams
which we currently use, while ``mpd``'s player backend (I think aplay or ffplay
from ffmpeg or something) cannot play AAC-plus streams, for example. That's why
``mopidy`` is the better ``mpd`` server.

There are many Android clients as well, so we can switch stations playing on
the raspi with our phone. There are two advantages:

* change station with phone [but this is no real use case] 
* ``mpc current`` is pretty fast, so we can get stream metadata whith much
  less effort compared to using ``mplayer`` [that is the only real plus] 

But that's about it. In raspi-radio, ``mpd`` can be used instead of
``mplayer`` (``./player.py --player mpd``), but is not the default b/c 

* ``mpd`` doesn't play all streams (probably aac-plus, see TODO file)
* we didn't care to install ``mopidy`` on the raspi yet, since the ``mplayer`` approach
  to stream metadata is good enough for now

