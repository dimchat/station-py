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
from typing import Optional, Union, List
from urllib.error import URLError

from startrek import DeparturePriority

from dimp import NetworkType, ID
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimsdk import ContentProcessor

from ...utils import Logging
from ...utils.nlp import ChatBot, Dialog
from ...common import CommonFacebook, CommonMessenger


class ChatTextContentProcessor(ContentProcessor, Logging):

    def __init__(self, facebook, messenger, bots: Union[list, ChatBot]):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__bots = bots
        self.__dialog: Optional[Dialog] = None

    @property
    def dialog(self) -> Dialog:
        if self.__dialog is None and len(self.__bots) > 0:
            d = Dialog()
            d.bots = self.__bots
            self.__dialog = d
        return self.__dialog

    def _query(self, content: Content, sender: ID) -> Optional[TextContent]:
        assert isinstance(content, TextContent), 'content error: %s' % content
        text = content.text
        if text.startswith('ping') or text.startswith('Ping'):
            # ping
            facebook = self.facebook
            assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
            user = facebook.current_user
            me = '@%s' % facebook.name(identifier=user.identifier)
            text = 'Pong%s from %s' % (text[4:], me)
            res = TextContent(text=text)
            group = content.group
            if group is not None:
                res.group = group
            return res
        if self.__bots is None:
            self.error('chat bots not set')
            return None
        dialog = self.dialog
        if dialog is None:
            # chat bots empty
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
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        at = '@%s' % facebook.name(identifier=receiver)
        if text.find(at) < 0:
            self.info('ignore group message that not querying me(%s): %s' % (at, text))
            return True
        # TODO: remove all '@nickname'
        text = text.replace(at, '')
        content.text = text

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        sender = msg.sender
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        nickname = facebook.name(identifier=sender)
        if self.__ignored(content=content, sender=sender, msg=msg):
            return []
        self.debug('received text message from %s: %s' % (nickname, content))
        res = self._query(content=content, sender=sender)
        if res is None:
            return []
        assert isinstance(res, TextContent)
        question = content.text
        answer = res.text
        group = content.group
        if group is None:
            # personal message
            self.debug('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            return [res]
        else:
            # group message
            self.debug('Group Dialog > %s(%s)@%s: "%s" -> "%s"' % (nickname, sender, group.name, question, answer))
            messenger = self.messenger
            assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % facebook
            if messenger.send_content(content=res, priority=DeparturePriority.NORMAL, receiver=group):
                text = 'Group message responded'
            else:
                text = 'Group message respond failed'
            return self._respond_receipt(text=text)
