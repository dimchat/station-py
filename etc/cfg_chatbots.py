# -*- coding: utf-8 -*-

"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""

import os

from common import Storage
from common import ChatBot, Tuling, XiaoI

etc = os.path.abspath(os.path.dirname(__file__))

# chat bot: Tuling
tuling_keys = Storage.read_json(path=os.path.join(etc, 'tuling', 'secret.js'))
tuling_ignores = [4003]


# chat bot XiaoI
xiaoi_keys = Storage.read_json(path=os.path.join(etc, 'xiaoi', 'secret.js'))
xiaoi_ignores = ['默认回复', '重复回复']


# create chat bot with name
def chat_bot(name: str) -> ChatBot:
    if 'tuling' == name:
        key = tuling_keys.get('api_key')
        tuling = Tuling(api_key=key)
        # ignore codes
        for item in tuling_ignores:
            if item not in tuling.ignores:
                tuling.ignores.append(item)
        return tuling
    elif 'xiaoi' == name:
        key = xiaoi_keys.get('app_key')
        secret = xiaoi_keys.get('app_secret')
        xiaoi = XiaoI(app_key=key, app_secret=secret)
        # ignore responses
        for item in xiaoi_ignores:
            if item not in xiaoi.ignores:
                xiaoi.ignores.append(item)
        return xiaoi
