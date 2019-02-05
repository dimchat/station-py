#!/usr/bin/bash

ps -fe | grep "dim\/station\/start.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dim/station/start.py >> /tmp/dims-${time}.log 2>&1 &
else
    echo "Station is running..." >&2
fi
