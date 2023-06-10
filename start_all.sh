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
stop "station/start.py"
stop "station/start_ct.py"
sleep 1
start "dims" "station/start_ct.py"
#start "dims" "station/start.py"

sleep 2

title "DIM Station Bridge"
restart octopus "robots/sbot_octopus.py"


#
#   Bots
#

title "DIM Search Engine"
restart search "robots/sbot_archivist.py"

title "DIM Group Assistant"
restart group "robots/gbot_assistant.py"

title "DIM Chat Bots"
restart ling "robots/chatbot_ling.py"
restart xiao "robots/chatbot_xiao.py"

title "DIM Chat Room"
restart chatroom "robots/chatroom_admin.py"

title "DIM File Server"
restart ftp "fileserver/start.py"

echo ""
echo "    >>> Done <<<"
echo ""
