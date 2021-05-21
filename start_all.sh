#!/usr/bin/env bash

root=$(cd "$(dirname "$0")" || exit;pwd)

start=${root}/shell_start.sh
stop=${root}/shell_stop.sh

# restart "name" "path/to/script.py"
function restart() {
    ${stop} "${root}/$2"
    sleep 1
    ${start} "$1" "${root}/$2"
}

function title() {
    echo ""
    echo "    >>> $1 <<<"
    echo ""
}


title "DIM Station"
restart dims "station/start.py"

sleep 2

title "DIM Station Bridge"
restart octopus "robots/sbot_octopus.py"

sleep 5

title "DIM Search Engine"
restart search "robots/sbot_archivist.py"

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
#
#title "Notification Pusher"
#restart pusher "station/pusher.py"

echo ""
echo "    >>> Done <<<"
echo ""
