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
    Chat Room Admin robot
    ~~~~~~~~~~~~~~~~~~~~~

    Chat room for web demo
"""

import sys
import os
import time
import weakref
from enum import IntEnum
from typing import Optional

from mkm.dos import JSONFile

from dimsdk import ID, EVERYONE
from dimsdk import InstantMessage
from dimsdk import ContentType, Content, Command, TextContent
from dimsdk import ForwardContent, ReceiptCommand, ProfileCommand
from dimsdk import ContentProcessor, CommandProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Log
from libs.common import SearchCommand
from libs.common import TextContentProcessor
from libs.client import ClientMessenger

from robots.config import g_facebook, g_keystore, g_station
from robots.config import g_database
from robots.config import load_user, create_client
from robots.config import chatroom_id
from robots.config import chat_bot


"""
    Messenger for Chat Room Admin robot
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore

# chat bot
g_messenger.context['bots'] = [chat_bot('tuling'), chat_bot('xiaoi')]
# current station
g_messenger.set_context('station', g_station)

g_facebook.messenger = g_messenger


#
#   Receipt Command Processor
#
class ReceiptCommandProcessor(CommandProcessor):

    def __init__(self, messenger: ClientMessenger):
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
class ChatTextContentProcessor(TextContentProcessor):

    def __init__(self, messenger: ClientMessenger):
        super().__init__(messenger=messenger)

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, TextContent), 'content error: %s' % content
        res = client.room.receive(content=content, sender=sender)
        if res is not None:
            return res
        return super().process(content=content, sender=sender, msg=msg)


# register
ContentProcessor.register(content_type=ContentType.Text, processor_class=ChatTextContentProcessor)
ContentProcessor.register(content_type=ContentType.Forward, processor_class=ForwardContentProcessor)
CommandProcessor.register(command=Command.RECEIPT, processor_class=ReceiptCommandProcessor)


def date_string(timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    return time.strftime('%Y%m%d', time.localtime(timestamp))


class StatKey(IntEnum):

    LOGIN = 1    # come back
    MESSAGE = 2  # send message


#
#  User activity stat
#
class Statistic:

    EXPIRES = 300  # 5 minutes

    def __init__(self):
        super().__init__()
        self.__login_stat: dict = None    # ID -> [time]
        self.__message_stat: dict = None  # ID -> int
        self.__stat_prefix: str = None
        self.__load_stat()

    def __load_stat(self):
        base = os.path.join(g_database.base_dir, 'stat')
        prefix = 'stat-' + date_string()
        # load login stat
        path = os.path.join(base, prefix + '-login.js')
        stat = JSONFile(path=path).read()
        if stat is None:
            self.__login_stat = {}
        else:
            self.__login_stat = stat
        # load message stat
        path = os.path.join(base, prefix + '-message.js')
        stat = JSONFile(path=path).read()
        if stat is None:
            self.__message_stat = {}
        else:
            self.__message_stat = stat
        # OK
        self.__stat_prefix = prefix
        self.__update_time = time.time()

    def __save_stat(self):
        now = time.time()
        if (now - self.__update_time) < self.EXPIRES:
            # wait for 5 minutes
            return
        self.__update_time = now

        base = os.path.join(g_database.base_dir, 'stat')
        prefix = self.__stat_prefix
        # save login stat
        path = os.path.join(base, prefix + '-login.js')
        JSONFile(path=path).write(container=self.__login_stat)
        # save message stat
        path = os.path.join(base, prefix + '-message.js')
        JSONFile(path=path).write(container=self.__message_stat)
        # OK
        prefix = 'stat-' + date_string()
        if prefix != self.__stat_prefix:
            # it's a new day!
            self.__login_stat = {}
            self.__message_stat = {}
            self.__stat_prefix = prefix

    def update(self, identifier: ID, stat: StatKey):
        if stat.value == StatKey.LOGIN.value:
            # login times
            array = self.__login_stat.get(identifier)
            if array is None:
                array = []
                self.__login_stat[identifier] = array
            array.append(time.time())
        elif stat.value == StatKey.MESSAGE.value:
            # message count
            count = self.__message_stat.get(identifier)
            if count is None:
                count = 0
            self.__message_stat[identifier] = count + 1
        else:
            raise TypeError('unknown stat type: %d' % stat)
        # OK
        self.__save_stat()

    def select(self) -> dict:
        return {
            'prefix': self.__stat_prefix,
            'login': self.__login_stat,
            'message': self.__message_stat,
        }


#
#  Chat history
#
class History:

    MAX = 100

    def __init__(self):
        super().__init__()
        self.__pool: list = []
        self.__load_history()

    @staticmethod
    def __path() -> str:
        base = os.path.join(g_database.base_dir, 'public')
        return os.path.join(base, 'chatroom-history.js')

    def __load_history(self):
        path = self.__path()
        # load chatroom history
        history = JSONFile(path=path).read()
        if history is None:
            return
        # convert contents
        array = []
        for item in history:
            content = Content(item)
            assert content is not None, 'content error: %s' % item
            array.append(content)
        self.__pool = array

    def __save_history(self):
        path = self.__path()
        # save chatroom history
        JSONFile(path=path).write(container=self.__pool)

    def push(self, content: ForwardContent):
        while len(self.__pool) >= self.MAX:
            self.__pool.pop(0)
        self.__pool.append(content)
        self.__save_history()

    def all(self) -> list:
        return self.__pool.copy()


class ChatRoom:

    EXPIRES = 600  # 10 minutes

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        self.__messenger = weakref.ref(messenger)
        self.__users: list = []  # ID
        self.__times: dict = {}  # ID -> time
        self.__statistic = Statistic()
        self.__history = History()

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger()

    @property
    def facebook(self):  # Facebook
        return self.messenger.facebook

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

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
            self.info('ignore ID: %s' % identifier)
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
            nickname = self.facebook.nickname(identifier=identifier)
            self.__broadcast(text='Welcome %s (%d)!' % (nickname, identifier.number))
            self.__statistic.update(identifier=identifier, stat=StatKey.LOGIN)
        return True

    def __broadcast(self, text: str):
        """ Broadcast text message to each online user """
        messenger = self.messenger
        facebook = self.facebook
        sender = facebook.current_user.identifier
        receiver = EVERYONE
        # create content
        content = TextContent.new(text=text)
        content.group = EVERYONE
        # create instant message
        i_msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        s_msg = messenger.encrypt_message(msg=i_msg)
        r_msg = messenger.sign_message(msg=s_msg)
        # split for online users
        users = self.__users.copy()
        users.reverse()
        messages = r_msg.split(members=users)
        # send one by one
        for msg in messages:
            messenger.send_message(msg=msg, callback=None, split=False)

    def __online(self) -> Content:
        """ Get online users """
        facebook = self.facebook
        users = self.__users.copy()
        users.reverse()
        results = {}
        for item in users:
            meta = facebook.meta(identifier=item)
            if meta is not None:
                results[item] = meta
        return SearchCommand.new(keywords=SearchCommand.ONLINE_USERS, users=users, results=results)

    def __stat(self) -> Content:
        info = self.__statistic.select()
        prefix = info['prefix']
        login = info['login']
        message = info['message']
        # user count
        u_cnt = len(login)
        # login count
        l_cnt = 0
        for u, a in login.items():
            l_cnt += len(a)
        # message count
        m_cnt = 0
        for u, c in message.items():
            m_cnt += c
        text = '[%s] %d user(s) login %d time(s), sent %d message(s)' % (prefix, u_cnt, l_cnt, m_cnt)
        return TextContent.new(text=text)

    def __push_history(self, receiver: ID) -> Content:
        messenger = self.messenger
        histories = self.__history.all()
        for content in histories:
            messenger.send_content(content=content, receiver=receiver)
        count = len(histories)
        if count == 0:
            text = 'No history record found.'
        elif count == 1:
            text = 'Got one chat history record.'
        else:
            text = 'Got %d chat history records' % count
        return TextContent.new(text=text)

    def forward(self, content: ForwardContent, sender: ID) -> Optional[Content]:
        if not self.__update(identifier=sender):
            return None
        self.info('forwarding message from: %s' % sender)
        self.__history.push(content=content)
        self.__statistic.update(identifier=sender, stat=StatKey.MESSAGE)
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
        if not self.__update(identifier=sender):
            return None
        self.info('got receipt from %s: %s' % (sender, cmd))
        return None

    def receive(self, content: Content, sender: ID) -> Optional[Content]:
        if not self.__update(identifier=sender):
            return None
        self.info('got message from %s' % sender)
        if isinstance(content, TextContent):
            text = content.text
            if text == 'show users':
                # search online users
                return self.__online()
            if text == 'show stat' or text == 'show statistics':
                # show statistics
                return self.__stat()
            if text == 'show history':
                # show chat history
                return self.__push_history(receiver=sender)
        return None


if __name__ == '__main__':

    user = load_user(chatroom_id)
    client = create_client(user=user, messenger=g_messenger)
    client.room = ChatRoom(client.messenger)
    # profile
    response = ProfileCommand.response(user.identifier, user.profile, user.meta)
    client.messenger.send_command(cmd=response)
