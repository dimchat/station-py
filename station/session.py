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
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""

import numpy

import dimp

from .utils import hex_encode


class Session:

    def __init__(self, identifier: dimp.ID):
        super().__init__()
        self.identifier = identifier
        self.request_handler = None
        self.session_key: str = hex_encode(bytes(numpy.random.bytes(32)))

    @property
    def valid(self) -> bool:
        return self.request_handler is not None


class SessionServer:

    def __init__(self):
        super().__init__()
        self.sessions = {}

    def session(self, identifier: dimp.ID) -> Session:
        sess = self.sessions.get(identifier)
        if sess is None:
            sess = Session(identifier=identifier)
            self.sessions[identifier] = sess
        return sess

    def valid(self, identifier: dimp.ID, request_handler) -> bool:
        sess = self.sessions.get(identifier)
        if sess is None or sess.request_handler is None:
            return False
        return sess.request_handler == request_handler

    def valid_sessions(self) -> list:
        sessions = self.sessions.copy()
        return [sess for sess in sessions.values() if sess.request_handler is not None]

    def clear_session(self, session: Session=None, identifier: dimp.ID=None, request_handler=None) -> bool:
        if session:
            ok = self.clear_session(identifier=session.identifier, request_handler=session.request_handler)
            session.request_handler = None
            return ok
        # clear by identifier
        sess = self.sessions.get(identifier)
        if sess is None:
            print('no such session: %s' % identifier)
            return False
        if request_handler is not None and sess.request_handler is not None:
            if sess.request_handler != request_handler:
                print('session error: %s' % identifier)
                return False
        # sess.request_handler = None
        self.sessions.pop(identifier)
        return True

    def reset_session(self, identifier: dimp.ID, session_key: str, request_handler) -> Session:
        session = self.session(identifier=identifier)
        if session.session_key == session_key:
            session.request_handler = request_handler
        return session

    def request_handler(self, identifier: dimp.ID):
        sess = self.sessions.get(identifier)
        if sess:
            return sess.request_handler

    def session_key(self, identifier: dimp.ID) -> str:
        sess = self.sessions.get(identifier)
        if sess:
            return sess.session_key
