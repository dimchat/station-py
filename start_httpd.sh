#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/webserver\/httpd.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/webserver/httpd.py >> /tmp/www-${time}.log 2>&1 &
    echo "DIM web server is started."
else
    echo "DIM web server is running..."
fi
