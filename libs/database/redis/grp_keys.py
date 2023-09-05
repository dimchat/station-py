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

from typing import Optional, Dict

from dimples import json_encode, json_decode, utf8_encode, utf8_decode
from dimples import ID

from .base import Cache


class GroupKeysCache(Cache):

    # group keys cached in Redis will be removed after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'dkd'

    @property  # Override
    def tbl_name(self) -> str:
        return 'group'

    """
        Encrypted keys
        ~~~~~~~~~~~~~~

        redis key: 'dkd.group.{GID}.{UID}.encrypted-keys'
    """
    def __cache_name(self, group: ID, sender: ID) -> str:
        return '%s.%s.%s.%s.encrypted-keys' % (self.db_name, self.tbl_name, group, sender)

    def group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        name = self.__cache_name(group=group, sender=sender)
        value = self.get(name=name)
        if value is not None:
            js = utf8_decode(data=value)
            assert js is not None, 'failed to decode string: %s' % value
            info = json_decode(string=js)
            assert info is not None, 'document error: %s' % value
            return info

    def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        js = json_encode(obj=keys)
        value = utf8_encode(string=js)
        name = self.__cache_name(group=group, sender=sender)
        self.set(name=name, value=value, expires=self.EXPIRES)
        return True
