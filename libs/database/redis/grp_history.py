# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from typing import Optional, Tuple, List

from dimples import json_encode, json_decode, utf8_encode, utf8_decode
from dimples import ID, ReliableMessage
from dimples import Command, GroupCommand

from ...utils import Logging

from .base import Cache


class GroupHistoryCache(Cache, Logging):

    # history command cached in Redis will be expired after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'group'

    """
        Group History Command
        ~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.group.{GID}.history'
    """
    def __cache_name(self, group: ID) -> str:
        return '%s.%s.%s.history' % (self.db_name, self.tbl_name, group)

    def load_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        name = self.__cache_name(group=group)
        value = self.get(name=name)
        if value is None:
            # cache not found
            return []
        js = utf8_decode(data=value)
        assert js is not None, 'failed to decode string: %s' % value
        array = json_decode(string=js)
        assert isinstance(array, List), 'history error: %s' % value
        histories = []
        for item in array:
            cmd = item.get('cmd')
            msg = item.get('msg')
            cmd = Command.parse(content=cmd)
            msg = ReliableMessage.parse(msg=msg)
            if cmd is None or msg is None:
                self.error(msg='group history error: %s' % item)
                continue
            his = (cmd, msg)
            histories.append(his)
        return histories

    def save_group_histories(self, group: ID, histories: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        array = []
        for his in histories:
            # assert len(his) == 2, 'group history error: %s' % his
            cmd = his[0]
            msg = his[1]
            item = {
                'cmd': cmd.dictionary,
                'msg': msg.dictionary,
            }
            array.append(item)
        js = json_encode(obj=array)
        value = utf8_encode(string=js)
        name = self.__cache_name(group=group)
        self.set(name=name, value=value, expires=self.EXPIRES)
        return True
