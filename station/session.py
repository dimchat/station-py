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
import random

import dimp

from .utils import hex_encode


class Session:

    def __init__(self, identifier: dimp.ID, request_handler):
        super().__init__()
        self.identifier: dimp.ID = identifier
        self.request_handler = request_handler
        self.client_address = request_handler.client_address
        # generate session key
        self.session_key: str = hex_encode(bytes(numpy.random.bytes(32)))
        self.valid = False


class SessionServer:

    def __init__(self):
        super().__init__()
        self.session_table = {}  # {identifier: [session]}

    def session_create(self, identifier: dimp.ID, request_handler) -> Session:
        """ Session factory """
        # 1. get all sessions with identifier
        sessions: list = self.session_table.get(identifier)
        if sessions is None:
            sessions = []
            self.session_table[identifier] = sessions
        else:
            # 2. check each session with request handler
            for sess in sessions:
                if sess.request_handler == request_handler:
                    # got one in cache
                    return sess
        # 3. create a new session
        sess = Session(identifier=identifier, request_handler=request_handler)
        sessions.append(sess)
        return sess

    def remove_session(self, session: Session=None, identifier: dimp.ID=None, request_handler=None):
        if session:
            return self.remove_session(identifier=session.identifier, request_handler=session.request_handler)
        # 1. check whether the session is exists
        sessions: list = self.search(identifier=identifier, request_handler=request_handler)
        if sessions is not None and len(sessions) == 1:
            session = sessions[0]
            # 2. remove it
            sessions = self.session_table.get(identifier)
            sessions.remove(session)
            # no more session for this identifier, remove it
            if len(sessions) == 0:
                self.session_table.pop(identifier)

    def search(self, identifier: dimp.ID, request_handler=None) -> list:
        """ Get session that identifier and request handler matched """
        sessions: list = self.session_table.get(identifier)
        # 1. if request handler not specified, return all sessions
        if request_handler is None:
            return sessions
        if sessions is not None:
            # 2. check session which has the same request handler
            for sess in sessions:
                if sess.request_handler == request_handler:
                    return [sess]

    def random_users(self, max_count=20) -> list:
        array = list(self.session_table.keys())
        count = len(array)
        if count < 2:
            return array
        elif count > max_count:
            count = max_count
        return random.sample(array, count)
