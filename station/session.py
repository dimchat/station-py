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

import numpy

import dimp

from .utils import hex_encode


class Session:

    def __init__(self, identifier: dimp.ID):
        super().__init__()
        self.identifier = identifier
        self.request_handler = None
        self.session_key = hex_encode(bytes(numpy.random.bytes(32)))


class SessionServer:

    def __init__(self):
        super().__init__()
        self.sessions = {}

    def session(self, identifier: dimp.ID) -> Session:
        if identifier in self.sessions:
            return self.sessions[identifier]
        else:
            sess = Session(identifier=identifier)
            self.sessions[identifier] = sess
            return sess

    def valid(self, identifier: dimp.ID, request_handler) -> bool:
        if identifier not in self.sessions:
            return False
        sess = self.sessions[identifier]
        return sess.request_handler == request_handler
