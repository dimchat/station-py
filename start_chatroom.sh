#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/robots\/chatroom_admin.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/chatroom_admin.py >> /tmp/chatroom-${time}.log 2>&1 &
    echo "Chat room is started."
else
    echo "Chat room is running..."
fi
