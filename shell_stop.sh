#!/usr/bin/env bash

exec=python3

function stop() {
    res=$(pgrep -f "${exec} .*$1")
    for pid in ${res[*]}
    do
        if [[ $((pid)) -gt 1 ]]
        then
            echo "stopping $1 ($((pid)))"
            kill -9 $((pid))
        fi
    done
}


# main
if [[ $# -eq 1 ]]
then
    stop "$1"
else
    echo ""
    echo "Usage:"
    echo "    $0 <path/to/script.py>"
    echo ""
fi
