#!/bin/bash

# Called when clicking a desktop icon. The DISPLAY setting is needed if we ssh
# into raspi but want the player to appear in the rpi-tft. Any additional
# options are passed to player.py (e.g. --format m3u).

DISPLAY=:0 python $(dirname $0)/player.py $@
