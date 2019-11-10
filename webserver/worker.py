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
    Delegate
    ~~~~~~~~
"""

from binascii import Error
from typing import Optional

from dimp import ID, Meta, Profile
from dimp import Content, MetaCommand, ProfileCommand

from libs.common import Log, base64_decode

from webserver.config import g_facebook


class Worker:

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def identifier(self, identifier: str) -> Optional[ID]:
        try:
            return g_facebook.identifier(string=identifier)
        except ValueError:
            self.error('ID error: %s' % identifier)

    def meta(self, identifier: str) -> Optional[Meta]:
        identifier = self.identifier(identifier)
        if identifier is None:
            return None
        info = g_facebook.meta(identifier=identifier)
        if info is None:
            self.info('meta not found: %s' % identifier)
        else:
            return info

    def profile(self, identifier: str) -> Optional[Profile]:
        identifier = self.identifier(identifier)
        if identifier is None:
            return None
        info = g_facebook.profile(identifier=identifier)
        if info is None:
            self.info('profile not found: %s' % identifier)
        else:
            return info

    def decode_data(self, data: str) -> Optional[bytes]:
        try:
            return base64_decode(data)
        except Error:
            self.error('data not base64: %s' % data)

    def decode_signature(self, signature: str) -> Optional[bytes]:
        try:
            return base64_decode(signature)
        except Error:
            self.error('signature not base64: %s' % signature)

    #
    #   interfaces
    #
    def query_meta(self, identifier: str) -> (int, Optional[Content]):
        # check ID
        identifier = self.identifier(identifier)
        if identifier is None:
            return 400, None  # Bad Request
        # get meta
        meta = self.meta(identifier)
        if meta is None:
            return 404, None  # Not Found
        # OK
        return 200, MetaCommand.new(identifier=identifier, meta=meta)

    def query_profile(self, identifier: str) -> (int, Optional[Content]):
        # check ID
        identifier = self.identifier(identifier)
        if identifier is None:
            return 400, None  # Bad Request
        # get profile
        profile = self.profile(identifier)
        if profile is None:
            return 404, None  # Not Found
        # get meta
        meta = self.meta(identifier)
        # OK
        return 200, ProfileCommand.new(identifier=identifier, meta=meta, profile=profile)

    def verify_message(self, sender: str, data: str, signature: str) -> int:
        # check ID
        identifier = self.identifier(sender)
        if identifier is None:
            return 400  # Bad Request
        # get meta
        meta = self.meta(identifier)
        if meta is None:
            return 404  # Not Found
        # check signature with data
        data = self.decode_data(data)
        signature = self.decode_signature(signature)
        if data is None or signature is None:
            return 412  # Precondition Failed
        if meta.key.verify(data=data, signature=signature):
            return 200  # OK
        else:
            return 403  # Forbidden
