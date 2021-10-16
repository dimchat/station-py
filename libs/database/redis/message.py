# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import time
from typing import List, Optional

from dimp import utf8_encode, utf8_decode, json_encode, json_decode
from dimp import ID, NetworkType
from dimp import ReliableMessage

from ...utils import get_msg_sig
from .base import Cache


class MessageCache(Cache):

    # only relay cached messages within 7 days
    EXPIRES = 3600 * 24 * 7  # seconds

    # only scan no more than 2048 messages for one time
    # (it's about 1MB at least)
    LIMIT = 2048

    @property  # Override
    def database(self) -> Optional[str]:
        return 'dkd'

    @property  # Override
    def table(self) -> str:
        return 'msg'

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dkd.msg.{ID}.{sig}'
        redis key: 'dkd.msg.{ID}.messages'
    """
    def __msg_key(self, identifier: ID, sig: str) -> str:
        return '%s.%s.%s.%s' % (self.database, self.table, identifier, sig)

    def __messages_key(self, identifier: ID) -> str:
        return '%s.%s.%s.messages' % (self.database, self.table, identifier)

    def save_message(self, msg: ReliableMessage) -> bool:
        if ignore_message(msg=msg):
            return False
        sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
        data = json_encode(o=msg.dictionary)
        msg_key = self.__msg_key(identifier=msg.receiver, sig=sig)
        self.set(name=msg_key, value=data, expires=self.EXPIRES)
        # append msg.signature to an ordered set
        messages_key = self.__messages_key(identifier=msg.receiver)
        self.zadd(name=messages_key, mapping={sig: msg.time})
        return True

    def remove_message(self, msg: ReliableMessage) -> bool:
        if ignore_message(msg=msg):
            return False
        receiver = msg.receiver
        sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
        value = utf8_encode(string=sig)
        # 1. delete msg.dictionary from redis server
        msg_key = self.__msg_key(identifier=receiver, sig=sig)
        self.delete(msg_key)
        # 2. delete msg.signature from the ordered set
        messages_key = self.__messages_key(identifier=receiver)
        self.zrem(messages_key, value)
        return True

    def messages(self, receiver: ID) -> List[ReliableMessage]:
        # 0. clear expired messages (7 days ago)
        key = self.__messages_key(identifier=receiver)
        expired = int(time.time()) - self.EXPIRES
        self.zremrangebyscore(name=key, min_score=0, max_score=expired)
        # 1. get number of messages
        count = self.zcard(name=key)
        if count < 1:
            return []
        if count > self.LIMIT:
            count = self.LIMIT
        array = []
        # 2. get all messages in the last 7 days
        signatures = self.zrange(name=key, start=0, end=(count - 1))
        for sig in signatures:
            # get messages by receiver & signature
            msg_key = self.__msg_key(identifier=receiver, sig=utf8_decode(data=sig))
            info = self.get(name=msg_key)
            if info is None:
                continue
            try:
                msg = json_decode(data=info)
                msg = ReliableMessage.parse(msg=msg)
                array.append(msg)
            except Exception as error:
                print('[REDIS] message error: %s' % error)
        return array


def is_broadcast_message(msg: ReliableMessage):
    if msg.receiver.is_broadcast:
        return True
    group = msg.group
    return group is not None and group.is_broadcast


def ignore_message(msg: ReliableMessage) -> bool:
    if is_broadcast_message(msg=msg):
        # ignore broadcast message
        return True
    if msg.sender.type == NetworkType.STATION:
        # ignore message from station
        return True
    if msg.receiver.type == NetworkType.STATION:
        # ignore message to station
        return True
