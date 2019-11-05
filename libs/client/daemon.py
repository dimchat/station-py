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
    Daemon Robot
    ~~~~~~~~~~~~

    Robot keep running
"""

import time
from typing import Union

from dimp import ID
from dimp import InstantMessage, Content, TextContent
from dimsdk import Station
from dimsdk import Dialog, ChatBot

from ..common import Facebook

from .robot import Robot


class Daemon(Robot):

    def __init__(self, identifier: ID):
        super().__init__(identifier=identifier)
        # dialog agent
        self.__dialog = Dialog()

    @property
    def bots(self) -> list:
        return self.__dialog.bots

    @bots.setter
    def bots(self, array: Union[list, ChatBot]):
        self.__dialog.bots = array

    def connect(self, station: Station) -> bool:
        if not super().connect(station=station):
            self.error('failed to connect station: %s' % station)
            return False
        self.info('connected to station: %s' % station)
        # handshake after connected
        time.sleep(0.5)
        self.info('%s is shaking hands with %s' % (self.identifier, station))
        return self.handshake()

    def receive_message(self, msg: InstantMessage) -> bool:
        if super().receive_message(msg=msg):
            return True
        facebook: Facebook = self.delegate
        sender = facebook.identifier(msg.envelope.sender)
        if sender.type.is_robot():
            self.info('Dialog > ignore message from another robot: %s' % msg.content)
            return False
        # check time
        now = int(time.time())
        dt = now - msg.envelope.time
        if dt > 600:
            self.info('Old message, ignore it: %s' % msg)
            return False
        content: Content = msg.content
        if content.group is not None:
            # group message
            if not isinstance(content, TextContent):
                self.info('Group Dialog > only support text message in polylogue: %s' % content)
                return False
            text = content.text
            if text is None:
                raise ValueError('text content error: %s' % content)
            # checking '@nickname'
            receiver = facebook.identifier(msg.envelope.receiver)
            at = '@%s' % facebook.nickname(identifier=receiver)
            self.info('Group Dialog > searching "%s" in "%s"...' % (at, text))
            if text.find(at) < 0:
                # ignore message that not querying me
                return False
            # TODO: remove all '@nickname'
            text = text.replace(at, '')
            content.text = text
        response = self.__dialog.query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            assert isinstance(content, TextContent)
            nickname = facebook.nickname(identifier=sender)
            question = content.text
            answer = response.text
            group = content.group
            if group is None:
                self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
                return self.send_content(content=response, receiver=sender)
            else:
                group = facebook.identifier(group)
                self.info('Group Dialog > %s(%s)@%s: "%s" -> "%s"' % (nickname, sender, group.name, question, answer))
                return self.send_content(content=response, receiver=group)
