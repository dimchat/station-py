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
    Chat Room Admin
    ~~~~~~~~~~~~~~~

    Chat bot for open meeting
"""

import time
from typing import Optional, Union, List, Dict, Set, Tuple

from dimples import ID, EVERYWHERE
from dimples import ReliableMessage
from dimples import ContentType, Content, ForwardContent, ArrayContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import ForwardContentProcessor as BaseForwardContentProcessor

from dimples import GroupCommand, JoinCommand, QuitCommand, QueryCommand
from dimples.client.cpu import GroupCommandProcessor

from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Logging
from libs.common import ReceiptCommand
from libs.client import ClientProcessor, ClientContentProcessorCreator
from libs.client import ClientMessenger

from robots.shared import start_bot


class Record:

    # If there is no action, the user will leave the room after 5 minutes.
    EXPIRES = 300

    def __init__(self, room: int, now: float):
        super().__init__()
        self.__room = room
        self.__expired = now + self.EXPIRES

    @property
    def room(self) -> int:
        return self.__room

    def is_expired(self, now: float) -> bool:
        return self.__expired < now

    def renew(self, now: float):
        self.__expired = now + self.EXPIRES


class Roster:

    def __init__(self):
        super().__init__()
        self.__users: Dict[int, Set[ID]] = {}  # rid => users
        self.__records: Dict[ID, Record] = {}  # uid => (rid, time)

    @property
    def is_empty(self) -> bool:
        return len(self.__users) == 0 and len(self.__records) == 0

    def purge(self, now: float) -> int:
        cnt = 0
        dictionary = dict(self.__records)
        for identifier in dictionary:
            record = dictionary.get(identifier)
            if record is not None and record.is_expired(now=now):
                # record is expired, remove user from the room
                users = self.__users.get(record.room)
                if users is not None:
                    users.discard(identifier)
                    if len(users) == 0:
                        self.__users.pop(record.room, None)
                # remove the record
                self.__records.pop(identifier, None)
                cnt += 1
        return cnt

    def add_user(self, identifier: ID, room: int, now: float) -> Set[ID]:
        """
        Add user in a room
        (this action will remove it from old room if exists)

        :param identifier: user ID
        :param room:       room ID
        :param now:        current time
        :return: None on error
        """
        # 1. check old record
        record = self.__records.get(identifier)
        if record is not None and record.room != room:
            # remove from old room
            users = self.__users.get(record.room)
            if users is not None:
                users.discard(identifier)
        # 2. update record
        self.__records[identifier] = Record(room=room, now=now)
        # 3. add user into new room
        users = self.__users.get(room)
        if users is None:
            users = set()
            self.__users[room] = users
        users.add(identifier)
        return users

    def refresh_user(self, identifier: ID, room: int, now: float) -> bool:
        """
        Update expired time for user in room

        :param identifier: user ID
        :param room:       room ID
        :param now:        current time
        :return: False on record not found or room ID not matched
        """
        record = self.__records.get(identifier)
        if record is not None and record.room == room:
            # update last active time
            record.renew(now=now)
            return True

    def remove_user(self, identifier: ID, room: int) -> bool:
        """
        Remove user from the room

        :param identifier: user ID
        :param room:       room ID
        :return: False on error
        """
        # 1. remove user from the room
        users = self.__users.get(room)
        if users is not None and identifier in users:
            users.discard(identifier)
            if len(users) == 0:
                self.__users.pop(room, None)
        # 2. remove user record
        record = self.__records.get(identifier)
        if record is not None and record.room == room:
            self.__records.pop(identifier, None)
            return True

    def check_user(self, identifier: ID, room: int, now: float) -> bool:
        """
        Check whether a user is in the room

        :param identifier: user ID
        :param room:       room ID
        :param now:        current time
        :return: False on record not found (or expired)
        """
        record = self.__records.get(identifier)
        if record is not None and record.room == room:
            # check last active time
            return not record.is_expired(now=now)

    def get_users(self, room: int, now: float) -> Set[ID]:
        """
        Get active users in this room

        :param room: room ID
        :param now:  current time
        :return: active users
        """
        active_users = set()
        users = self.__users.get(room)
        if users is not None:
            for identifier in users:
                if self.check_user(identifier=identifier, room=room, now=now):
                    # record exists and not expired yet
                    active_users.add(identifier)
        return active_users


#
#   Command/Content Processing Units
#


def pack_responses(content: Content) -> List[Content]:
    if content is None:
        return []
    # check for broadcast message
    group = content.group
    if group is not None and group.is_broadcast:
        # if respond it as a broadcast message, the room info will be exposed to everyone,
        # so we pack it to an ArrayContent to be encrypted before responding.
        content = ArrayContent.create(contents=[content])
    return [content]


class JoinCommandProcessor(GroupCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, JoinCommand), 'join command error: %s' % content
        # enter the room
        res = g_room.join(content=content, msg=msg)
        return pack_responses(content=res)


class QuitCommandProcessor(GroupCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QuitCommand), 'quit command error: %s' % content
        # exit the room
        res = g_room.quit(content=content, msg=msg)
        return pack_responses(content=res)


class QueryCommandProcessor(GroupCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QueryCommand), 'query command error: %s' % content
        # query room info
        res = g_room.query(content=content, msg=msg)
        return pack_responses(content=res)


class ForwardContentProcessor(BaseForwardContentProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ForwardContent), 'forward content error: %s' % content
        if 'room' not in content:
            # not for chatroom
            return super().process(content=content, msg=msg)
        # broadcast to the room
        res = g_room.forward(content=content, msg=msg)
        return pack_responses(content=res)


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # forward
        if msg_type == ContentType.FORWARD:
            return ForwardContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # join
        if cmd == GroupCommand.JOIN:
            return JoinCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # quit
        if cmd == GroupCommand.QUIT:
            return QuitCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # query
        if cmd == GroupCommand.QUERY:
            return QueryCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ChatRoom(Logging):

    EXPIRES = 600  # purge rosters every 10 minutes

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        self.__messenger = messenger
        facebook = messenger.facebook
        current = facebook.current_user
        assert current is not None, 'Bot ID not set'
        self.__current = current.identifier
        # user caches
        self.__rosters: Dict[str, Roster] = {}  # app_id => roster
        self.__expired: float = 0.0             # next purge time

    def __purge(self, now: float):
        if now < self.__expired:
            # not expired yet
            return -1
        else:
            # update expired time for next purge
            self.__expired = now + self.EXPIRES
        dictionary = dict(self.__rosters)
        for app in dictionary:
            roster = dictionary.get(app)
            if roster is not None and roster.purge(now=now) > 0:
                if roster.is_empty:
                    # remove it
                    self.__rosters.pop(app, None)
        return len(dictionary) - len(self.__rosters)

    def __prepare(self, content: Content) -> Tuple[int, str, Roster]:
        room = content.get_int('room')
        app = content.get_str('app')
        if app is None:
            app = APP_ID
        roster = self.__rosters.get(app)
        if roster is None:
            roster = Roster()
            self.__rosters[app] = roster
        return room, app, roster

    def __welcome(self, user: ID, room: int, content: JoinCommand):
        # TODO: broadcast 'Welcome %s!' to users in this room
        pass

    def __goodbye(self, user: ID, room: int, content: QuitCommand):
        # TODO: broadcast 'Goodbye %s!' to users in this room
        pass

    def join(self, content: JoinCommand, msg: ReliableMessage) -> Content:
        # try to clear expired records
        now = time.time()
        self.__purge(now=now)
        # prepare for chatroom
        room, app, roster = self.__prepare(content=content)
        # add user into the room
        sender = msg.sender
        # TODO: authorization
        users = roster.add_user(identifier=sender, room=room, now=now)
        if users is None or len(users) == 0:
            self.error(msg='failed to enter the room: %d, %s' % (room, sender))
            text = 'User is unauthorized to enter the room'
            res = ReceiptCommand.create(text=text, msg=msg)
        else:
            self.__welcome(user=sender, room=room, content=content)
            # respond users via group command
            res = GroupCommand.reset(group=GRP_ID)
            res['users'] = ID.revert(array=users)
        # respond with room ID
        res['room'] = room
        res['app'] = app
        return res

    def quit(self, content: QuitCommand, msg: ReliableMessage) -> Content:
        # prepare for chatroom
        room, app, roster = self.__prepare(content=content)
        # remove user from the room
        sender = msg.sender
        # TODO: authorization
        if roster.remove_user(identifier=sender, room=room):
            self.__goodbye(user=sender, room=room, content=content)
            text = 'Exited the room'
        else:
            self.error(msg='sender not in the room: %d, %s' % (room, sender))
            text = 'User not in the room'
        # respond with room ID
        res = ReceiptCommand.create(text=text, msg=msg)
        res['room'] = room
        res['app'] = app
        return res

    def query(self, content: QueryCommand, msg: ReliableMessage) -> Content:
        # prepare for chatroom
        room, app, roster = self.__prepare(content=content)
        # check users
        now = time.time()
        users = roster.get_users(room=room, now=now)
        sender = msg.sender
        if sender in users:
            # renew expired time
            roster.refresh_user(identifier=sender, room=room, now=now)
            # respond users via group command
            res = GroupCommand.reset(group=GRP_ID)
            res['users'] = ID.revert(array=users)
        else:
            self.error(msg='sender not in the room: %d, %s, %s' % (room, sender, users))
            text = 'User not in the room'
            res = ReceiptCommand.create(text=text, msg=msg)
        # respond with room ID
        res['room'] = room
        res['app'] = app
        return res

    def forward(self, content: ForwardContent, msg: ReliableMessage) -> Content:
        # prepare for chatroom
        room, app, roster = self.__prepare(content=content)
        # check users
        now = time.time()
        users = roster.get_users(room=room, now=now)
        sender = msg.sender
        r_msg = content.forward
        if sender != r_msg.sender:
            self.error(msg='sender not match: %s, %s' % (sender, r_msg.sender))
            text = 'Sender not match'
        elif sender in users:
            roster.refresh_user(identifier=sender, room=room, now=now)
            # broadcast to other users
            users.discard(sender)
            messenger = self.__messenger
            bot = self.__current
            for item in users:
                messenger.send_content(sender=bot, receiver=item, content=content)
            text = 'Message forwarded to %d user(s)' % len(users)
        else:
            self.error(msg='sender not in the room: %d, %s, %s' % (room, sender, users))
            text = 'Sender not in the room: %d' % room
        # respond with room ID
        res = ReceiptCommand.create(text=text, msg=msg)
        res['room'] = room
        res['app'] = app
        return res


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'

APP_ID = 'chat.dim.room'
GRP_ID = ID.create(name='chatroom', address=EVERYWHERE)  # 'chatroom@everywhere'


if __name__ == '__main__':
    terminal = start_bot(default_config=DEFAULT_CONFIG,
                         app_name='ChatRoom: Administrator',
                         ans_name='administrator',
                         processor_class=BotMessageProcessor)
    g_room = ChatRoom(messenger=terminal.messenger)
