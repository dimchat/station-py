#!/usr/bin/bash

ps -fe | grep "\/srv\/dim\/station\/start.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dim/station/start.py >> /tmp/dims-${time}.log 2>&1 &
else
    echo "Station is running..."
fi

#ps -fe | grep "\/srv\/dim\/fileserver\/server.py" | grep -v grep
#if [ $? -ne 0 ]
#then
#    time=`date +%Y%m%d-%H%M%S`
#    stdbuf -oL /usr/local/bin/python3 /srv/dim/fileserver/server.py >> /tmp/cdn-${time}.log 2>&1 &
#else
#    echo "File server is running..."
#fi
