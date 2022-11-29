# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

import os
from typing import Optional

from dimp import ID, Meta

from .base import Storage


class MetaStorage(Storage):
    """
        Meta file for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/meta.js'
        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'meta.js')

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving meta into: %s' % path)
        return self.write_json(container=meta.dictionary, path=path)

    def meta(self, identifier: ID) -> Optional[Meta]:
        path = self.__path(identifier=identifier)
        self.info('Loading meta from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return Meta.parse(meta=dictionary)
