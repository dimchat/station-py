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
from typing import Optional, List

from dimples import utf8_encode, utf8_decode, json_encode, json_decode
from dimples import ID
from dimples import ReliableMessage

from ...utils import get_msg_sig
from .base import Cache


class MessageCache(Cache):

    # only relay cached messages within 7 days
    EXPIRES = 3600 * 24 * 7  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'dkd'

    @property  # Override
    def tbl_name(self) -> str:
        return 'msg'

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dkd.msg.{ID}.{sig}'
        redis key: 'dkd.msg.{ID}.messages'
    """
    def __msg_cache_name(self, identifier: ID, sig: str) -> str:
        return '%s.%s.%s.%s' % (self.db_name, self.tbl_name, identifier, sig)

    def __messages_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.messages' % (self.db_name, self.tbl_name, identifier)

    def save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
        # 1. save message: 'dkd.msg.{RECEIVER}.{SIG}
        msg_key = self.__msg_cache_name(identifier=receiver, sig=sig)
        js = json_encode(obj=msg.dictionary)
        value = utf8_encode(string=js)
        self.set(name=msg_key, value=value, expires=self.EXPIRES)
        # 2. append sig to an ordered set
        messages_key = self.__messages_cache_name(identifier=receiver)
        self.zadd(name=messages_key, mapping={sig: msg.time})
        return True

    def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
        # 1. delete message: 'dkd.msg.{RECEIVER}.{SIG}
        msg_key = self.__msg_cache_name(identifier=receiver, sig=sig)
        self.delete(msg_key)
        # 2. delete sig from the ordered set
        messages_key = self.__messages_cache_name(identifier=receiver)
        self.zrem(messages_key, utf8_encode(string=sig))
        return True

    def reliable_messages(self, receiver: ID, limit: int = 1024) -> List[ReliableMessage]:
        assert limit > 0, 'message limit error: %d' % limit
        # 0. clear expired messages (7 days ago)
        key = self.__messages_cache_name(identifier=receiver)
        expired = int(time.time()) - self.EXPIRES
        self.zremrangebyscore(name=key, min_score=0, max_score=expired)
        # 1. make range
        total = self.zcard(name=key)
        assert total >= 0, 'message cache error: %s' % key
        if total <= limit:
            start = 0
            end = total
        else:
            start = total - limit
            end = total
        # 2. get all messages in the last 7 days
        array = []
        signatures = self.zrange(name=key, start=start, end=end)
        for sig in signatures:
            # get messages by receiver & signature
            msg_key = self.__msg_cache_name(identifier=receiver, sig=utf8_decode(data=sig))
            value = self.get(name=msg_key)
            if value is None:
                continue
            try:
                js = utf8_decode(data=value)
                dictionary = json_decode(string=js)
                msg = ReliableMessage.parse(msg=dictionary)
                array.append(msg)
            except Exception as error:
                print('[REDIS] message error: %s => %s' % (error, value))
        return array
