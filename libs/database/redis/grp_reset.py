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

from typing import Optional, Tuple

from dimples import json_encode, json_decode, utf8_encode, utf8_decode
from dimples import ID, ReliableMessage
from dimples import ResetCommand, ResetGroupCommand

from .base import Cache


class ResetGroupCache(Cache):

    # reset command cached in Redis will be expired after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'group'

    """
        Reset Group Command
        ~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.group.{GID}.reset'
    """
    def __cache_name(self, group: ID) -> str:
        return '%s.%s.%s.reset' % (self.db_name, self.tbl_name, group)

    def load_reset(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        """
        Get 'reset' group command message

        :param group: group ID
        :return: (*, None) when cache not found
        """
        name = self.__cache_name(group=group)
        value = self.get(name=name)
        if value is None:
            # cache not found
            return ResetGroupCommand(group=group), None
        js = utf8_decode(data=value)
        assert js is not None, 'failed to decode string: %s' % value
        info = json_decode(string=js)
        assert info is not None, 'command error: %s' % value
        cmd = info.get('cmd')
        msg = info.get('msg')
        if cmd is not None:
            cmd = ResetGroupCommand(content=cmd)
        if msg is not None:
            msg = ReliableMessage.parse(msg=msg)
        return cmd, msg

    def save_reset(self, group: ID, content: Optional[ResetCommand], msg: Optional[ReliableMessage]) -> bool:
        """
        Cache 'reset' command message

        :param group:   group ID
        :param content: 'reset' command, None for placeholder
        :param msg:     'reset' message, None for placeholder
        :return: True
        """
        if content is not None:
            content = content.dictionary
        if msg is not None:
            msg = msg.dictionary
        table = {
            'cmd': content,
            'msg': msg,
        }
        js = json_encode(obj=table)
        value = utf8_encode(string=js)
        name = self.__cache_name(group=group)
        self.set(name=name, value=value, expires=self.EXPIRES)
        return True
