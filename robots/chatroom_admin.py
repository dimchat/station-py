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
    Chatroom admin robot
    ~~~~~~~~~~~~~~~~~~~~

    Chat room for web demo
"""

import sys
import os
import time
import weakref
from typing import Optional

from dimsdk import ID
from dimsdk import InstantMessage
from dimsdk import ContentType, Content, Command, TextContent
from dimsdk import ForwardContent, ReceiptCommand, ProfileCommand
from dimsdk import ContentProcessor, CommandProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Log, SearchCommand

from robots.config import load_user, create_client
from robots.config import chatroom_id


#
#   Receipt Command Processor
#
class ReceiptCommandProcessor(CommandProcessor):

    def __init__(self, messenger):
        super().__init__(messenger=messenger)

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, ReceiptCommand), 'receipt command error: %s' % content
        return client.room.receipt(cmd=content, sender=sender)


#
#   Forward Content Processor
#
class ForwardContentProcessor(ContentProcessor):

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, ForwardContent), 'forward content error: %s' % content
        r_msg = content.forward

        # [Forward Protocol]
        # do it again to drop the wrapper,
        # the secret inside the content is the real message
        s_msg = self.messenger.verify_message(msg=r_msg)
        if s_msg is None:
            # TODO: save this message in a queue to wait meta response
            # raise ValueError('failed to verify message: %s' % r_msg)
            return None

        # call client to process it
        return client.room.forward(content=content, sender=sender)


#
#   Text Content Processor
#
class TextContentProcessor(ContentProcessor):

    def __init__(self, messenger):
        super().__init__(messenger=messenger)

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, TextContent), 'content error: %s' % content
        return client.room.receive(content=content, sender=sender)


# register
ContentProcessor.register(content_type=ContentType.Text, processor_class=TextContentProcessor)
ContentProcessor.register(content_type=ContentType.Forward, processor_class=ForwardContentProcessor)
CommandProcessor.register(command=Command.RECEIPT, processor_class=ReceiptCommandProcessor)


class ChatRoom:

    EXPIRES = 600  # 10 minutes

    def __init__(self, messenger):
        super().__init__()
        self.__messenger = weakref.ref(messenger)
        self.__users: list = []  # ID
        self.__times: dict = {}  # ID -> time

    @property
    def messenger(self):  # Messenger
        return self.__messenger()

    @property
    def facebook(self):  # Facebook
        return self.messenger.facebook

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def refresh(self):
        now = time.time()
        index = 0
        while index < len(self.__users):
            item = self.__users[index]
            last = self.__times.get(item)
            if last is None:
                self.__users.pop(index)
                continue
            if (now - last) > self.EXPIRES:
                self.__users.pop(index)
                self.__times.pop(item)
                continue
            index += 1

    def update(self, identifier: ID) -> bool:
        if identifier.name != 'web-demo':
            self.error('ignore ID: %s' % identifier)
            return False
        if self.__times.get(identifier):
            self.__users.remove(identifier)
            exists = True
        else:
            exists = False
        self.__times[identifier] = time.time()
        self.__users.append(identifier)
        self.refresh()
        if not exists:
            messenger = self.messenger
            facebook = self.facebook
            nickname = facebook.nickname(identifier=identifier)
            content = TextContent.new(text='Welcome new guest: %s(%d)' % (nickname, identifier.number))
            users = self.__users.copy()
            users.reverse()
            for item in users:
                messenger.send_content(content=content, receiver=item)
        return True

    def forward(self, content: ForwardContent, sender: ID) -> Optional[Content]:
        if not self.update(identifier=sender):
            return None
        self.info('forwarding message from: %s' % sender)
        # forwarding
        messenger = self.messenger
        users = self.__users.copy()
        users.reverse()
        for item in users:
            if item == sender:
                continue
            messenger.send_content(content=content, receiver=item)
        return ReceiptCommand.new(message='message forwarded')

    def receipt(self, cmd: ReceiptCommand, sender: ID) -> Optional[Content]:
        if not self.update(identifier=sender):
            return None
        self.info('got receipt from %s' % sender)
        return None

    def receive(self, content: Content, sender: ID) -> Optional[Content]:
        if not self.update(identifier=sender):
            return None
        self.info('got message from %s' % sender)
        if isinstance(content, TextContent):
            if content.text == 'show users':
                # search online users
                facebook = self.facebook
                users = self.__users.copy()
                users.reverse()
                results = {}
                for item in users:
                    meta = facebook.meta(identifier=item)
                    if meta is not None:
                        results[item] = meta
                return SearchCommand.new(keywords=SearchCommand.ONLINE_USERS, users=users, results=results)
        return None


if __name__ == '__main__':

    user = load_user(chatroom_id)
    client = create_client(user)
    client.room = ChatRoom(client.messenger)
    # profile
    cmd = ProfileCommand.response(user.identifier, user.profile, user.meta)
    client.messenger.send_command(cmd)
