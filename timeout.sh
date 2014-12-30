#!/bin/bash

timeout=$1
shift

$@ &
last=$!
for i in $(seq 1 $timeout); do
    ##echo "wait ... $i / $timeout"
    sleep 1
done

kill -15 $last
sleep 1

if ps aux | grep -v grep | grep -q $last; then
    kill -9 $last
fi    

exit 0
