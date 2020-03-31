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

"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""

import time
import weakref
from typing import Optional

from dimp import ID, Meta, Profile

from libs.common import CommonFacebook


class ClientFacebook(CommonFacebook):

    EXPIRES = 3600  # profile expires (1 hour)
    EXPIRES_KEY = 'expires'

    def __init__(self):
        super().__init__()
        self.__messenger = None

    @property
    def messenger(self):  # ClientMessenger
        return self.__messenger()

    @messenger.setter
    def messenger(self, value):
        self.__messenger = weakref.ref(value)

    def meta(self, identifier: ID) -> Optional[Meta]:
        if identifier.is_broadcast:
            # broadcast ID has not meta
            return None
        # try from database
        meta = super().meta(identifier=identifier)
        if meta is not None and 'key' in meta:
            # meta exists
            return meta
        # query from DIM network
        self.messenger.query_meta(identifier=identifier)

    def profile(self, identifier: ID) -> Optional[Profile]:
        # try from database
        profile = super().profile(identifier=identifier)
        if profile is not None and 'data' in profile:
            # check expired time
            timestamp = time.time()
            expires = profile.get(self.EXPIRES_KEY)
            if expires is None:
                # set expired time
                profile[self.EXPIRES_KEY] = timestamp + self.EXPIRES
                return profile
            elif expires > timestamp:
                # not expired yet
                return profile
        # query from DIM network
        self.messenger.query_profile(identifier=identifier)
        return profile
