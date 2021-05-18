#!/usr/bin/bash

time=$(date +%Y%m%d-%H%M%S)
exec=/usr/local/bin/python3
root=/srv/dims
logs=/tmp

function stop() {
    res=$(pgrep -f "${root}/$1")
    for pid in ${res[*]}
    do
        if [[ $((pid)) -ne 0 ]]
        then
            echo "stopping ${root}/$1 ($((pid)))..."
            kill -9 $((pid))
            sleep 1
        fi
    done
}

function start() {
    echo "starting ${root}/$1 ..."
    stdbuf -oL ${exec} "${root}/$1" >> "${logs}/$2-${time}.log" 2>&1 &
}

# restart name main.py
stop "$2"
start "$2" "$1"
