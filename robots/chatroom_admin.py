#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Chat Room Admin bot
    ~~~~~~~~~~~~~~~~~~~

    Chat room for web demo
"""

import time
from enum import IntEnum
from typing import Optional, Union, List

from startrek import DeparturePriority

from dimples import ID, EVERYONE
from dimples import Envelope, InstantMessage, ReliableMessage
from dimples import ContentType, Content, TextContent, ForwardContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseContentProcessor, BaseCommandProcessor
from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Logging
from libs.common import ReceiptCommand
from libs.common import CommonFacebook
from libs.client import SearchCommand
from libs.client import ChatTextContentProcessor
from libs.client import ClientProcessor, ClientContentProcessorCreator
from libs.client import ClientMessenger
from libs.client.cpu.text import get_name

from robots.shared import GlobalVariable
from robots.shared import chat_bots
from robots.shared import start_bot


#
#   Receipt Command Processor
#
class ReceiptCommandProcessor(BaseCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReceiptCommand), 'receipt command error: %s' % content
        return [g_room.receipt(content=content, sender=msg.sender)]


#
#   Forward Content Processor
#
class ForwardContentProcessor(BaseContentProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ForwardContent), 'forward content error: %s' % content
        # TODO: get from 'secrets'
        r_msg = content.forward

        # [Forward Protocol]
        messenger = self.messenger
        assert isinstance(messenger, ClientMessenger), 'messenger error: %s' % messenger
        s_msg = messenger.verify_message(msg=r_msg)
        if s_msg is None:
            # TODO: save this message in a queue to wait meta response
            # raise ValueError('failed to verify message: %s' % r_msg)
            return []

        # call client to process it
        res = g_room.forward(content=content, sender=msg.sender)
        if res is None:
            return []
        else:
            return [res]


#
#   Text Content Processor
#
class BotTextContentProcessor(ChatTextContentProcessor):

    def __init__(self, facebook, messenger):
        shared = GlobalVariable()
        bots = chat_bots(names=['tuling', 'xiaoi'], shared=shared)  # chat bots
        super().__init__(facebook=facebook, messenger=messenger, bots=bots)

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'content error: %s' % content
        res = g_room.receive(content=content, sender=msg.sender)
        if res is not None:
            return [res]
        return super().process(content=content, msg=msg)


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return BotTextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # forward
        if msg_type == ContentType.FORWARD:
            return ForwardContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # receipt
        if cmd == ReceiptCommand.RECEIPT:
            return ReceiptCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


def date_string(timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    return time.strftime('%Y%m%d', time.localtime(timestamp))


class StatKey(IntEnum):

    LOGIN = 1    # come back
    MESSAGE = 2  # send message


#
#  Chat history
#
class History:

    MAX = 100

    def __init__(self):
        super().__init__()
        self.__pool: list = []

    def push(self, content: ForwardContent):
        while len(self.__pool) >= self.MAX:
            self.__pool.pop(0)
        self.__pool.append(content)

    def all(self) -> list:
        return self.__pool.copy()


class ChatRoom(Logging):

    EXPIRES = 600  # 10 minutes

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        self.__messenger = messenger
        self.__users: list = []  # ID
        self.__times: dict = {}  # ID -> time
        self.__history = History()

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    def __refresh(self):
        """ Remove timeout user(s) """
        now = time.time()
        while len(self.__users) > 0:
            item = self.__users[0]
            last = self.__times.get(item)
            if last is None:
                # should not happen
                self.error('user active time lost: %s' % item)
                self.__users.pop(0)
                continue
            if (now - last) > self.EXPIRES:
                self.__users.pop(0)
                self.__times.pop(item)
                continue
            # users sorted by time
            break

    def __update(self, identifier: ID) -> bool:
        """ Update user active status """
        if identifier.name != 'web-demo':
            self.warning('ignore ID: %s' % identifier)
            return False
        if self.__times.get(identifier):
            self.__users.remove(identifier)
            exists = True
        else:
            exists = False
        self.__times[identifier] = time.time()
        self.__users.append(identifier)
        self.__refresh()
        if not exists:
            nickname = get_name(identifier=identifier, facebook=self.facebook)
            self.__broadcast(text='Welcome %s (%s)!' % (nickname, identifier))
        return True

    def __broadcast(self, text: str):
        """ Broadcast text message to each online user """
        messenger = self.messenger
        sender = self.facebook.current_user.identifier
        receiver = EVERYONE
        # create content
        content = TextContent.create(text=text)
        content.group = EVERYONE
        # create instant message
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        s_msg = messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to broadcast message: %s' % text
        r_msg = messenger.sign_message(msg=s_msg)
        # split for online users
        users = self.__users.copy()
        users.reverse()
        messages = r_msg.split(members=users)
        # send one by one
        for msg in messages:
            messenger.send_reliable_message(msg=msg, priority=DeparturePriority.NORMAL)

    def __online(self) -> Content:
        """ Get online users """
        users = self.__users.copy()
        users.reverse()
        results = {}
        for item in users:
            meta = self.facebook.meta(identifier=item)
            if meta is not None:
                results[item] = meta
        return SearchCommand(keywords=SearchCommand.ONLINE_USERS, users=users, results=results)

    def __push_history(self, receiver: ID) -> Content:
        messenger = self.messenger
        histories = self.__history.all()
        for content in histories:
            messenger.send_content(sender=None, receiver=receiver, content=content, priority=DeparturePriority.NORMAL)
        count = len(histories)
        if count == 0:
            text = 'No history record found.'
        elif count == 1:
            text = 'Got one chat history record.'
        else:
            text = 'Got %d chat history records' % count
        return TextContent.create(text=text)

    def forward(self, content: ForwardContent, sender: ID) -> Optional[Content]:
        if not self.__update(identifier=sender):
            return None
        self.debug('forwarding message from: %s' % sender)
        self.__history.push(content=content)
        # forwarding
        messenger = self.messenger
        users = self.__users.copy()
        users.reverse()
        for item in users:
            if item == sender:
                continue
            messenger.send_content(sender=None, receiver=item, content=content, priority=DeparturePriority.NORMAL)
        return ReceiptCommand.create(text='message forwarded')

    def receipt(self, content: ReceiptCommand, sender: ID) -> Optional[Content]:
        if not self.__update(identifier=sender):
            return None
        self.debug('got receipt from %s: %s' % (sender, content))
        return None

    def receive(self, content: Content, sender: ID) -> Optional[Content]:
        if not self.__update(identifier=sender):
            return None
        self.debug('got message from %s' % sender)
        if isinstance(content, TextContent):
            text = content.text
            if text == 'show users':
                # search online users
                return self.__online()
            if text == 'show history':
                # show chat history
                return self.__push_history(receiver=sender)
        return None


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


if __name__ == '__main__':
    terminal = start_bot(default_config=DEFAULT_CONFIG,
                         app_name='ChatRoom: Administrator',
                         ans_name='administrator',
                         processor_class=BotMessageProcessor)
    g_room = ChatRoom(messenger=terminal.messenger)
