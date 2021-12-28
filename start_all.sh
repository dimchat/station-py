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


title "DIM Station"
stop "station/start.py"
stop "station/receptionist.py"
stop "station/archivist.py"
stop "station/pusher.py"
stop "station/monitor.py"
sleep 2
start "monitor" "station/monitor.py"
start "pusher" "station/pusher.py"
start "search" "station/archivist.py"
start "sabrina" "station/receptionist.py"
start "dims" "station/start.py"

sleep 2

title "DIM Station Bridge"
restart octopus "robots/sbot_octopus.py"

#title "DIM Group Assistant"
#restart group "robots/gbot_assistant.py"
#
#title "DIM Chat Bots"
#restart ling "robots/chatbot_ling.py"
#restart xiao "robots/chatbot_xiao.py"
#
#title "DIM Chat Room"
#restart chatroom "robots/chatroom_admin.py"
#
#title "DIM Web Server"
#restart www "webserver/httpd.py"

echo ""
echo "    >>> Done <<<"
echo ""
