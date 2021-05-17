#!/usr/bin/bash


ps -fe | grep "\/srv\/dims\/robots\/sbot_archivist.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=$(date +%Y%m%d-%H%M%S)
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/sbot_archivist.py >> /tmp/archivist-"${time}".log 2>&1 &
    echo "DIM Search Engine is started."
else
    echo "DIM Search Engine is running."
fi
