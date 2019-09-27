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

from common import Tuling, XiaoI


class Dialog:

    def __init__(self):
        super().__init__()
        # chat bots
        array = [
            Tuling(api_key='8cbbdaf0baea412296800444895a75be'),
            XiaoI(app_key='open1_1BALCbHT4f2k', app_secret='mzMzWQ6kpUztmVvCDXyy'),
        ]
        # random them
        self.bots: list = random.sample(array, len(array))

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
        if isinstance(content, TextContent):
            question = content.text
            answer = self.__ask(question=question, sender=sender)
            if answer is not None:
                return TextContent.new(text=answer)
        # TEST: response client with the same message here
        return content
