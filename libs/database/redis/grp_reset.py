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
        Reset info for Groups
        ~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.group.{ID}.reset'
    """
    def __reset_key(self, identifier: ID) -> str:
        return '%s.%s.%s.reset' % (self.db_name, self.tbl_name, identifier)

    def save_reset(self, group: ID, content: ResetCommand, msg: ReliableMessage) -> bool:
        """ Save reset command & message into Redis Server """
        dictionary = {'cmd': content.dictionary, 'msg': msg.dictionary}
        js = json_encode(obj=dictionary)
        value = utf8_encode(string=js)
        key = self.__reset_key(identifier=group)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def load_reset(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        key = self.__reset_key(identifier=group)
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None, None
        js = utf8_decode(data=value)
        dictionary = json_decode(string=js)
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        if cmd is not None:
            cmd = ResetGroupCommand(cmd)
        return cmd, ReliableMessage.parse(msg=msg)

    def reset_command(self, group: ID) -> Optional[ResetCommand]:
        cmd, _ = self.load_reset(group=group)
        return cmd

    def reset_message(self, group: ID) -> Optional[ReliableMessage]:
        _, msg = self.load_reset(group=group)
        return msg
