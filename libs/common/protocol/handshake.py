# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Handshake Command Protocol
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. (C-S) handshake start
    2. (S-C) handshake again with new session
    3. (C-S) handshake start with new session
    4. (S-C) handshake success
"""

from enum import IntEnum
from typing import Optional, Any, Dict

from dimsdk import Command, BaseCommand


class HandshakeState(IntEnum):
    Init = 0
    Start = 1    # C -> S, without session key(or session expired)
    Again = 2    # S -> C, with new session key
    Restart = 3  # C -> S, with new session key
    Success = 4  # S -> C, handshake accepted


class HandshakeCommand(BaseCommand):
    """
        Handshake Command
        ~~~~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            cmd     : "handshake",    // command name
            message : "Hello world!", // "DIM?", "DIM!"
            session : "{SESSION_ID}", // session key
        }
    """
    HANDSHAKE = 'handshake'

    def __init__(self, content: Optional[Dict[str, Any]] = None,
                 message: Optional[str] = None, session: Optional[str] = None):
        if content is None:
            super().__init__(cmd=self.HANDSHAKE)
        else:
            super().__init__(content=content)
        if message is not None:
            self['message'] = message
        if session is not None:
            self['session'] = session
        self.__state = handshake_state(message=message, session=session)

    @property
    def message(self) -> str:
        return self['message']

    @property
    def session(self) -> Optional[str]:
        return self.get('session')

    @property
    def state(self) -> HandshakeState:
        return self.__state

    #
    #   Factories
    #

    @classmethod
    def offer(cls, session: str = None) -> Command:
        """
        Create client-station handshake offer

        :param session: Old session key
        :return: HandshakeCommand object
        """
        return HandshakeCommand(message='Hello world!', session=session)

    @classmethod
    def ask(cls, session: str) -> Command:
        """
        Create station-client handshake again with new session

        :param session: New session key
        :return: HandshakeCommand object
        """
        return HandshakeCommand(message='DIM?', session=session)

    @classmethod
    def accepted(cls, session: str = None) -> Command:
        """
        Create station-client handshake success notice

        :return: HandshakeCommand object
        """
        return HandshakeCommand(message='DIM!', session=session)

    start = offer       # (1. C->S) first handshake, without session
    again = ask         # (2. S->C) ask client to handshake with new session key
    restart = offer     # (3. C->S) handshake with new session key
    success = accepted  # (4. S->C) notice the client that handshake accepted


def handshake_state(message: Optional[str], session: Optional[str]) -> HandshakeState:
    if message is None or len(message) == 0:
        return HandshakeState.Init
    if message == 'DIM!' or message == 'OK!':
        return HandshakeState.Success
    if message == 'DIM?':
        return HandshakeState.Again
    if session is None or len(session) == 0:
        return HandshakeState.Start
    else:
        return HandshakeState.Restart
