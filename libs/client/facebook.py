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

from typing import Optional

from dimp import ID, Meta, Document

from libs.utils import Singleton
from libs.common import CommonFacebook


@Singleton
class ClientFacebook(CommonFacebook):

    def meta(self, identifier: ID) -> Optional[Meta]:
        info = super().meta(identifier=identifier)
        if info is None:
            if identifier.is_broadcast:
                return None
            # TODO: query from DIM network
            pass
        return info

    def document(self, identifier: ID, doc_type: Optional[str]='*') -> Optional[Document]:
        info = super().document(identifier=identifier, doc_type=doc_type)
        if info is None or self.is_expired_document(document=info):
            # TODO: query from DIM network
            pass
        return info
