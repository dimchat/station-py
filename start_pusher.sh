#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/station\/pusher.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/station/pusher.py >> /tmp/notification_pusher-${time}.log 2>&1 &
    echo "DIM Notification Pusher is started."
else
    echo "DIM Notification Pusher is running..."
fi
