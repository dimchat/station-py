#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/station\/start.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/station/start.py >> /tmp/dims-${time}.log 2>&1 &
else
    echo "Station is running..."
fi

#ps -fe | grep "\/srv\/dims\/fileserver\/server.py" | grep -v grep
#if [ $? -ne 0 ]
#then
#    time=`date +%Y%m%d-%H%M%S`
#    stdbuf -oL /usr/local/bin/python3 /srv/dims/fileserver/server.py >> /tmp/cdn-${time}.log 2>&1 &
#else
#    echo "File server is running..."
#fi
