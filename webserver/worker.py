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

from dimp import ID, Meta, Profile

from libs.common import Log, base64_decode

from webserver.config import g_facebook


class Worker:

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def identifier(self, identifier: str) -> ID:
        try:
            return g_facebook.identifier(string=identifier)
        except ValueError:
            self.error('ID error: %s' % identifier)

    def meta(self, identifier: ID) -> Meta:
        info = g_facebook.meta(identifier=identifier)
        if info is None:
            self.info('meta not found: %s' % identifier)
        else:
            return info

    def profile(self, identifier: ID) -> Profile:
        info = g_facebook.profile(identifier=identifier)
        if info is None:
            self.info('profile not found: %s' % identifier)
        else:
            return info

    def decode_data(self, data: str) -> bytes:
        try:
            return base64_decode(data)
        except Error:
            self.error('data not base64: %s' % data)

    def decode_signature(self, signature: str) -> bytes:
        try:
            return base64_decode(signature)
        except Error:
            self.error('signature not base64: %s' % signature)
