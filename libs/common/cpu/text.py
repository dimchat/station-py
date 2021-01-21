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
    Text Content Processor
    ~~~~~~~~~~~~~~~~~~~~~~

"""

import time
from typing import Optional
from urllib.error import URLError

from dimp import NetworkType, ID
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ContentProcessor

from libs.utils import Log
from libs.utils.nlp import Dialog

from ..messenger import CommonMessenger


class TextContentProcessor(ContentProcessor):

    def __init__(self):
        super().__init__()
        self.__dialog: Dialog = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def messenger(self) -> CommonMessenger:
        return super().messenger

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        ContentProcessor.messenger.__set__(self, transceiver)

    @property
    def bots(self) -> list:
        array = self.messenger.get_context(key='bots')
        if array is None:
            array = []
        return array

    @property
    def dialog(self) -> Dialog:
        if self.__dialog is None:
            d = Dialog()
            d.bots = self.bots
            self.__dialog = d
        return self.__dialog

    def __query(self, content: Content, sender: ID) -> TextContent:
        dialog = self.dialog
        try:
            return dialog.query(content=content, sender=sender)
        except URLError as error:
            self.error('%s' % error)

    def __ignored(self, content: Content, sender: ID, msg: ReliableMessage) -> bool:
        # check robot
        if sender.type in [NetworkType.ROBOT, NetworkType.STATION]:
            # self.info('Dialog > ignore message from another robot: %s' % msg.content)
            return True
        # check time
        now = int(time.time())
        dt = now - msg.time
        if dt > 600:
            self.info('Old message, ignore it: %s' % msg)
            return True
        # check group message
        if content.group is None:
            # not a group message
            return False
        text = content.text
        if text is None:
            raise ValueError('text content error: %s' % content)
        # checking '@nickname'
        receiver = msg.receiver
        at = '@%s' % self.facebook.name(identifier=receiver)
        self.info('Group Dialog > searching "%s" in "%s"...' % (at, text))
        if text.find(at) < 0:
            self.info('ignore group message that not querying me: %s' % text)
            return True
        # TODO: remove all '@nickname'
        text = text.replace(at, '')
        content.text = text

    #
    #   main
    #
    def process(self, content: Content, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        sender = msg.sender
        nickname = self.facebook.name(identifier=sender)
        if self.__ignored(content=content, sender=sender, msg=msg):
            return None
        self.info('Received text message from %s: %s' % (nickname, content))
        response = self.__query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            question = content.text
            answer = response.text
            group = content.group
            if group is None:
                # personal message
                self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            else:
                # group message
                self.info('Group Dialog > %s(%s)@%s: "%s" -> "%s"' % (nickname, sender, group.name, question, answer))
                if self.messenger.send_content(sender=None, receiver=group, content=response):
                    text = 'Group message responded'
                    return ReceiptCommand(message=text)
                else:
                    text = 'Group message respond failed'
                    return ReceiptCommand(message=text)
            return response


# register
ContentProcessor.register(content_type=ContentType.TEXT, cpu=TextContentProcessor())
