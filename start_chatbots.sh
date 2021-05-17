#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/robots\/chatbot_ling.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=$(date +%Y%m%d-%H%M%S)
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/chatbot_ling.py >> /tmp/bot_ling-"${time}".log 2>&1 &
    echo "DIM Chat Bot: Lingling is started."
else
    echo "DIM Chat Bot: Lingling is running."
fi


ps -fe | grep "\/srv\/dims\/robots\/chatbot_xiao.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=$(date +%Y%m%d-%H%M%S)
    stdbuf -oL /usr/local/bin/python3 /srv/dims/robots/chatbot_xiao.py >> /tmp/bot_xiao-"${time}".log 2>&1 &
    echo "DIM Chat Bot: Xiaoxiao is started."
else
    echo "DIM Chat Bot: Xiaoxiao is running."
fi
