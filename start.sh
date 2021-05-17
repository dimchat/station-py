#!/usr/bin/bash

echo ">>> Starting DIM Station ..."
/srv/dims/start_station.sh

sleep 2

echo ">>> Starting DIM Station Bridge ..."
/srv/dims/start_octopus.sh

sleep 5

echo ">>> Starting DIM Search Engine ..."
/srv/dims/start_archivist.sh

#echo ">>> Starting DIM Group Assistant ..."
#/srv/dims/start_assistant.sh
#
#echo ">>> Starting DIM Chat Bots ..."
#/srv/dims/start_chatbots.sh
#
#echo ">>> Starting DIM Chat Room ..."
#/srv/dims/start_chatroom.sh
