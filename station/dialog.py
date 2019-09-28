# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

"""
    Dialog Robot
    ~~~~~~~~~~~~

    Dialog for chatting with station
"""

import random

from dimp import ID
from dimp import Content, TextContent

from common import Log
from common import Tuling, XiaoI

from .config import g_facebook
from .cfg_chatbots import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores


def chat_bots() -> list:
    array = []
    # chat bot: Tuling
    if tuling_keys is not None:
        key = tuling_keys.get('api_key')
        tuling = Tuling(api_key=key)
        # ignore codes
        for item in tuling_ignores:
            if item not in tuling.ignores:
                tuling.ignores.append(item)
        array.append(tuling)
    # chat bot: XiaoI
    if xiaoi_keys is not None:
        key = xiaoi_keys.get('app_key')
        secret = xiaoi_keys.get('app_secret')
        xiaoi = XiaoI(app_key=key, app_secret=secret)
        # ignore responses
        for item in xiaoi_ignores:
            if item not in xiaoi.ignores:
                xiaoi.ignores.append(item)
        array.append(xiaoi)
    # random them
    count = len(array)
    if count > 1:
        return random.sample(array, count)
    else:
        return array


class Dialog:

    def __init__(self):
        super().__init__()
        # chat bot list
        self.bots = chat_bots()

    def __ask(self, question: str, sender: ID) -> str:
        # try each chat robots
        index = 0
        for robot in self.bots:
            answer = robot.ask(question=question, user=sender.number)
            if answer is None:
                index += 1
                continue
            # got the answer
            if index > 0:
                # move this bot to front
                self.bots.remove(robot)
                self.bots.insert(0, robot)
            return answer

    def talk(self, content: Content, sender: ID) -> Content:
        nickname = g_facebook.nickname(identifier=sender)
        if isinstance(content, TextContent):
            question = content.text
            answer = self.__ask(question=question, sender=sender)
            Log.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            if answer is not None:
                return TextContent.new(text=answer)
        # TEST: response client with the same message here
        Log.info('Dialog > message from %s(%s): %s' % (nickname, sender, content))
        return content
