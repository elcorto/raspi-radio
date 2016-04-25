raspi-radio
===========

About
-----

A very minimalistic Tkinter GUI for playing web radio streams. Meant to be used
on a Raspberry Pi with a touchscreen TFT display (like the `watterott
<https://github.com/watterott/RPi-Display>`_ RPi display [that's what we use]
or the `adafruit <http://www.adafruit.com/product/1601>`_ PiTFT display, both
320x240), running Raspbian and an X server (no SDL/Pygame). Tkinter and LXDE on
the Raspberry Pi model B+ don't use much resources, so that's OK.

See ``screenshots/`` for some images.

There is no connection to icecast servers, so no search by genre etc. Also, we
use ``mplayer`` for playing streams and we therefore don't need ``mpd`` and
``mpc`` (but see below).

Start the radio with::

    ./player.py


Streams
-------

The default playlist is 

::
    
    ~/.raspi-radio/streams.json

which looks like this::

    [
        {"name": "soma 80s", 
         "url":  "http://ice.somafm.com/u80s"},
        {"name": "soma groove", 
         "url":  "http://ice.somafm.com/groovesalad"},
        ...
    ]      
    
We store the last played stream in ``last_stream.json`` and automatically start
that the next time. 

Install
-------

Copy all files to the raspi::
    
    [me@mybox ~/.../git/raspi-radio]$ scp -r * raspi:raspi-radio/
    [me@mybox ~/.../git/raspi-radio]$ scp ~/.raspi-radio/streams* raspi:.raspi-radio/

On the raspi, make sure that the radio starts up when X comes up, but not when
we log in via ssh. We use an Xsession startup script::
    
    pi@raspi ~/raspi-radio $ sudo cp 200raspi-radio /etc/X11/Xsession.d/
    pi@raspi ~/raspi-radio $ sudo chmod ugo+r /etc/X11/Xsession.d/200raspi-radio

Install desktop icon if you wish::

    pi@raspi ~/raspi-radio $ cp desktop/icon-raspi-radio-white.png ~/.icons/
    pi@raspi ~/raspi-radio $ cp desktop/raspi-radio.desktop ~/Desktop/


Usage
-----
::

    ./player.py

See also ``player.py -h``, ``start.sh`` and ``200raspi-radio`` for how to actually use 
it, including automatic start after boot.


Thanks
------

Icons are an adapted version of
http://www.flaticon.com/free-icon/volume-bars-player-music_477 (creative
commons license http://creativecommons.org/licenses/by/3.0/legalcode). We added
a white background (the original was transparent).


Raspberry Pi install and setup
==============================

Download the Raspbian image from https://github.com/watterott/RPi-Display, then
flash onto the sd card which you will put into the raspi later::
    
    sudo dd if=2014-06-20-wheezy-raspbian-2014-07-25-fbtft-rpi-display-rev2.img of=/dev/mmcblk0

Connect to ethernet, boot and ssh into the raspi::

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

    [i] vim mercurial mplayer2 ntp
    
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
    
    [m] /etc/kbd/config
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

