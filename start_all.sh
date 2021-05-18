#!/usr/bin/bash

echo ""
echo ">>> Starting DIM Station ..."
echo ""
/srv/dims/shell_restart.sh dims station/start.py

sleep 2

echo ""
echo ">>> Starting DIM Station Bridge ..."
echo ""
/srv/dims/shell_restart.sh bridge robots/sbot_octopus.py

sleep 5

echo ""
echo ">>> Starting DIM Search Engine ..."
echo ""
/srv/dims/shell_restart.sh search robots/sbot_archivist.py

#echo ""
#echo ">>> Starting DIM Group Assistant ..."
#echo ""
#/srv/dims/shell_restart.sh group robots/gbot_assistant.py
#
#echo ""
#echo ">>> Starting DIM Chat Bots ..."
#echo ""
#/srv/dims/shell_restart.sh chat_ling robots/chatbot_ling.py
#/srv/dims/shell_restart.sh chat_xiao robots/chatbot_xiao.py
#
#echo ""
#echo ">>> Starting DIM Chat Room ..."
#echo ""
#/srv/dims/shell_restart.sh chatroom robots/chatroom_admin.py
#
#echo ""
#echo ">>> Starting Web Server ..."
#echo ""
#/srv/dims/shell_restart.sh www webserver/httpd.py
#
#echo ""
#echo ">>> Starting Notification Pusher ..."
#echo ""
#/srv/dims/shell_restart.sh pusher station/pusher.py

echo ""
echo ">>> Done."
echo ""
