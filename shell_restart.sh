#!/usr/bin/env bash

exec=python3
logs=/tmp

function stop() {
    res=$(pgrep -f "$1")
    for pid in ${res[*]}
    do
        if [[ $((pid)) -gt 1 ]]
        then
            echo "stopping $1 ($((pid)))"
            kill -9 $((pid))
        fi
    done
}

function start() {
    now=$(date +%Y%m%d-%H%M%S)
    log=${logs}/$2-${now}.log
    echo "starting $1 > ${log}"
    ${exec} "$1" > "${log}" 2>&1 &
}


# main
if [[ $# -eq 2 ]]
then
    # restart name main.py
    stop "$2"
    sleep 1
    start "$2" "$1"
else
    echo ""
    echo "Usages:"
    echo "    $0 <name> <path/to/main.py>"
    echo ""
fi
