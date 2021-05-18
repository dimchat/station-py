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
from typing import Optional, Union
from urllib.error import URLError

from dimp import NetworkType, ID
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ContentProcessor

from ...utils import Logging
from ...utils.nlp import ChatBot, Dialog

from ..messenger import CommonMessenger


class TextContentProcessor(ContentProcessor, Logging):

    def __init__(self, bots: Union[list, ChatBot]):
        super().__init__()
        self.__bots = bots
        self.__dialog: Optional[Dialog] = None

    @property
    def messenger(self) -> CommonMessenger:
        return super().messenger

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        ContentProcessor.messenger.__set__(self, transceiver)

    @property
    def dialog(self) -> Dialog:
        if self.__dialog is None and len(self.__bots) > 0:
            d = Dialog()
            d.bots = self.__bots
            self.__dialog = d
        return self.__dialog

    def _query(self, content: Content, sender: ID) -> Optional[TextContent]:
        if self.__bots is None:
            self.error('chat bots not set')
            return None
        dialog = self.dialog
        if dialog is None:
            return None
        try:
            return dialog.query(content=content, sender=sender)
        except URLError as error:
            self.error('%s' % error)

    def __ignored(self, content: Content, sender: ID, msg: ReliableMessage) -> bool:
        # check robot
        if sender.type in [NetworkType.ROBOT, NetworkType.STATION]:
            self.info('ignore message from another robot: %s, "%s"' % (sender, content.get('text')))
            return True
        # check time
        now = int(time.time())
        dt = now - msg.time
        if dt > 600:
            # Old message, ignore it
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
        if text.find(at) < 0:
            self.info('ignore group message that not querying me(%s): %s' % (at, text))
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
        self.debug('received text message from %s: %s' % (nickname, content))
        response = self._query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            question = content.text
            answer = response.text
            group = content.group
            if group is None:
                # personal message
                self.debug('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
                return response
            else:
                # group message
                self.debug('Group Dialog > %s(%s)@%s: "%s" -> "%s"' % (nickname, sender, group.name, question, answer))
                if self.messenger.send_content(sender=None, receiver=group, content=response):
                    text = 'Group message responded'
                    return ReceiptCommand(message=text)
                else:
                    text = 'Group message respond failed'
                    return ReceiptCommand(message=text)


# register
ContentProcessor.register(content_type=ContentType.TEXT, cpu=TextContentProcessor(bots=[]))
