#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/station\/start.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=$(date +%Y%m%d-%H%M%S)
    stdbuf -oL /usr/local/bin/python3 /srv/dims/station/start.py >> /tmp/dims-"${time}".log 2>&1 &
    echo "DIM Station is started."
else
    echo "DIM Station is running."
fi
