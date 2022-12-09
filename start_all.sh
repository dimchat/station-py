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

archivist="archivist@2Ph6zsUBL8rbimRArb2f539j64JUJJQoDpZ"
assistant="assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq"
ling="lingling@2PemMVAvxpuVZw2SYwwo11iBBEBb7gCvDHa"
xiao="xiaoxiao@2PhVByg7PhEtYPNzW5ALk9ygf6wop1gTccp"
#admin="chatroom-admin@2Pc5gJrEQYoz9D9TJrL35sA3wvprNdenPi7"

title "DIM Search Engine"
stop "robots/sbot_archivist.py"
start search "robots/sbot_archivist.py ${archivist}"

title "DIM Group Assistant"
stop "robots/gbot_assistant.py"
start group "robots/gbot_assistant.py ${assistant}"

title "DIM Chat Bots"
stop "robots/chatbot_ling.py"
start ling "robots/chatbot_ling.py ${ling}"
stop "robots/chatbot_xiao.py"
start xiao "robots/chatbot_xiao.py ${xiao}"

#title "DIM Chat Room"
#stop "robots/chatroom_admin.py"
#start chatroom "robots/chatroom_admin.py ${admin}"

#title "DIM Web Server"
#restart www "webserver/httpd.py"

echo ""
echo "    >>> Done <<<"
echo ""
