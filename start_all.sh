#!/usr/bin/env bash

root=$(cd "$(dirname "$0")" || exit;pwd)
restart=${root}/shell_restart.sh

echo ""
echo ">>> Starting DIM Station ..."
echo ""
${restart} dims "${root}/station/start.py"

sleep 2

echo ""
echo ">>> Starting DIM Station Bridge ..."
echo ""
${restart} octopus "${root}/robots/sbot_octopus.py"

sleep 5

echo ""
echo ">>> Starting DIM Search Engine ..."
echo ""
${restart} search "${root}/robots/sbot_archivist.py"

#echo ""
#echo ">>> Starting DIM Group Assistant ..."
#echo ""
#${restart} group "${root}/robots/gbot_assistant.py"
#
#echo ""
#echo ">>> Starting DIM Chat Bots ..."
#echo ""
#${restart} ling "${root}/robots/chatbot_ling.py"
#${restart} xiao "${root}/robots/chatbot_xiao.py"
#
#echo ""
#echo ">>> Starting DIM Chat Room ..."
#echo ""
#${restart} chatroom "${root}/robots/chatroom_admin.py"
#
#echo ""
#echo ">>> Starting Web Server ..."
#echo ""
#${restart} www "${root}/webserver/httpd.py"
#
#echo ""
#echo ">>> Starting Notification Pusher ..."
#echo ""
#${restart} pusher "${root}/station/pusher.py"

echo ""
echo ">>> Done."
echo ""
