#!/usr/bin/env bash

root=$(cd "$(dirname "$0")" || exit;pwd)

start_shell=${root}/shell_start.sh
stop_shell=${root}/shell_stop.sh

# start "name" "path/to/script.py"
function start() {
    ${start_shell} "$1" "${root}/$2"
}

# stop "path/to/script.py"
function stop() {
    ${stop_shell} "${root}/$1"
}

# restart "name" "path/to/script.py"
function restart() {
    stop "$2"
    sleep 1
    start "$1" "$2"
}

function title() {
    echo ""
    echo "    >>> $1 <<<"
    echo ""
}


#
#   Station & Bridges
#

title "DIM Station"
restart "dims" "station/start.py"

sleep 2

title "DIM Station Bridge"
restart octopus "sbots/sbot_octopus.py"


#
#   Service Bots
#

#title "DIM Search Engine"
#restart search "sbots/sbot_archivist.py"
#
#title "DIM Push Center"
#restart apns "sbots/sbot_announcer.py"
#
#title "DIM Monitor"
#restart monitor "sbots/sbot_monitor.py"

#
#   File Server
#

#title "DIM File Server"
#restart ftp "fileserver/start.py"

echo ""
echo "    >>> Done <<<"
echo ""
