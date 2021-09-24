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

import json
from typing import Optional

from dimp import ID, Meta

from .base import Cache


class MetaCache(Cache):

    # meta cached in Redis Server will be removed after a week
    EXPIRES = 3600 * 24 * 7  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'meta'

    """
        Meta key for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.meta.{ID}'
    """
    def __key(self, identifier: ID) -> str:
        return '%s.%s.%s' % (self.database, self.table, identifier)

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        dictionary = meta.dictionary
        info = json.dumps(dictionary)
        value = bytes(info)
        key = self.__key(identifier=identifier)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def meta(self, identifier: ID) -> Optional[Meta]:
        key = self.__key(identifier=identifier)
        value = self.get(name=key)
        if value is None:
            return None
        dictionary = json.loads(value)
        assert dictionary is not None, 'meta error: %s' % value
        return Meta.parse(meta=dictionary)
