#!/usr/bin/env bash

exec=python3
logs=/tmp

time=$(date +%Y%m%d-%H%M%S)

function start() {
    log=${logs}/$1-${time}.log
    echo "starting $2 >> ${log}"
    ${exec} "$2" >> "${log}" 2>&1 &
}


# main
if [[ $# -eq 2 ]]
then
    start "$1" "$2"
else
    echo ""
    echo "Usage:"
    echo "    $0 <name> <path/to/script.py>"
    echo ""
fi
