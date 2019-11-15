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

from dimp import ID
from dimp import InstantMessage
from dimp import ContentType, Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ContentProcessor
from dimsdk import Dialog

from ..utils import Log


class TextContentProcessor(ContentProcessor):

    def __init__(self, messenger):
        super().__init__(messenger=messenger)
        self.__dialog: Dialog = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def bots(self) -> list:
        array = self.get_context('bots')
        if array is None:
            array = []
            self.set_context('bots', array)
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

    def __ignored(self, content: Content, sender: ID, msg: InstantMessage) -> bool:
        # check robot
        if sender.type.is_robot() or sender.type.is_station():
            self.info('Dialog > ignore message from another robot: %s' % msg.content)
            return True
        # check time
        now = int(time.time())
        dt = now - msg.envelope.time
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
        receiver = self.facebook.identifier(msg.envelope.receiver)
        at = '@%s' % self.facebook.nickname(identifier=receiver)
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
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        nickname = self.facebook.nickname(identifier=sender)
        self.info('Received text message from %s: %s' % (nickname, content))
        if self.__ignored(content=content, sender=sender, msg=msg):
            return None
        response = self.__query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            question = content.text
            answer = response.text
            group = self.facebook.identifier(content.group)
            if group is None:
                # personal message
                self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            else:
                # group message
                self.info('Group Dialog > %s(%s)@%s: "%s" -> "%s"' % (nickname, sender, group.name, question, answer))
                if self.messenger.send_content(content=response, receiver=group):
                    text = 'Group message responded'
                    return ReceiptCommand.new(message=text)
                else:
                    text = 'Group message respond failed'
                    return ReceiptCommand.new(message=text)
            return response


# register
ContentProcessor.register(content_type=ContentType.Text, processor_class=TextContentProcessor)
