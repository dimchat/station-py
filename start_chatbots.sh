#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/robots\/chatbot_ling.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/chatbot_ling.py >> /tmp/bot_ling-${time}.log 2>&1 &
    echo "Lingling is started."
else
    echo "Lingling is running..."
fi


ps -fe | grep "\/srv\/dims\/robots\/chatbot_xiao.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/chatbot_xiao.py >> /tmp/bot_xiao-${time}.log 2>&1 &
    echo "Xiaoxiao is started."
else
    echo "Xiaoxiao is running..."
fi
