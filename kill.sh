#!/bin/sh

# Use to kill a player started with "start.sh".

ps aux | grep -E 'start\.sh|player' | awk '!/grep/ {print $2}'  | xargs kill -9
