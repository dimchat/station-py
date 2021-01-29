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

"""
    Facebook for station
    ~~~~~~~~~~~~~~~~~~~~
"""

import weakref
from typing import Optional

from dimp import ID, Meta, Document

from libs.utils import Singleton
from libs.common import CommonFacebook, CommonMessenger


@Singleton
class ServerFacebook(CommonFacebook):

    def __init__(self):
        super().__init__()
        self.__messenger: Optional[weakref.ReferenceType] = None

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = weakref.ref(transceiver)

    # DISCUSS: broadcast meta to every stations when user login,
    #          no need to query other stations time by time
    def meta(self, identifier: ID) -> Optional[Meta]:
        info = super().meta(identifier=identifier)
        if info is None:
            # query from DIM network
            messenger = self.messenger
            if messenger is not None and not identifier.is_broadcast:
                # broadcast ID has not meta
                messenger.query_meta(identifier=identifier)
        return info

    # DISCUSS: broadcast document to every stations when user upload it,
    #          no need to query other stations time by time
    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        info = super().document(identifier=identifier, doc_type=doc_type)
        if info is None or self.is_expired_document(document=info):
            # query from DIM network
            messenger = self.messenger
            if messenger is not None and not identifier.is_broadcast:
                # broadcast ID has not meta
                messenger.query_document(identifier=identifier)
        return info
