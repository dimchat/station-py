# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
from typing import Union

from dimp import ID
from dimp import Content, TextContent, AudioContent

from .chatbot import ChatBot


class Dialog:

    def __init__(self):
        super().__init__()
        # chat bot candidates
        self.__bots: list = []

    @property
    def bots(self) -> list:
        return self.__bots

    @bots.setter
    def bots(self, array: Union[list, ChatBot]):
        if isinstance(array, list):
            count = len(array)
            if count > 1:
                # set bots with random order
                self.__bots = random.sample(array, len(array))
            else:
                self.__bots = array
        elif isinstance(array, ChatBot):
            self.__bots = [array]
        else:
            raise ValueError('bots error: %s' % array)

    def ask(self, question: str, sender: ID) -> str:
        # try each chat robots
        index = 0
        for robot in self.__bots:
            answer = robot.ask(question=question, user=sender.number)
            if answer is None:
                index += 1
                continue
            # got the answer
            if index > 0:
                # move this bot to front
                self.__bots.remove(robot)
                self.__bots.insert(0, robot)
            return answer

    def query(self, content: Content, sender: ID) -> TextContent:
        if isinstance(content, TextContent):
            # text dialog
            question = content.text
            answer = self.ask(question=question, sender=sender)
            if answer is not None:
                response = TextContent.new(text=answer)
                group = content.group
                if group is not None:
                    response.group = group
                return response
        elif isinstance(content, AudioContent):
            # TODO: Automatic Speech Recognition
            pass
