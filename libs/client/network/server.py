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
    Station Server
    ~~~~~~~~~~~~~~

    Local station
"""

import weakref
from abc import abstractmethod
from typing import Optional

from dimp import ID, User
from dimp import Envelope, InstantMessage, ReliableMessage
from dimsdk import HandshakeCommand
from dimsdk import Station, MessengerDelegate, CompletionHandler

from ...utils import Log
from ...common import CommonMessenger

from .connection import Connection, ConnectionDelegate


class Server(Station, MessengerDelegate, ConnectionDelegate):
    """
        Remote Station
        ~~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int = 9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.__conn: Optional[Connection] = None
        self.__messenger: Optional[weakref.ReferenceType] = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def connection_reconnected(self, connection):
        self.info('connection reconnected: %s, %s:%d' % (self.identifier, self.host, self.port))
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        messenger.reconnected()
        self.handshake()

    def connect(self):
        if self.__conn is None:
            conn = Connection()
            conn.delegate = self
            conn.messenger = self.messenger
            conn.connect(host=self.host, port=self.port)
            self.__conn = conn

    def disconnect(self):
        if self.__conn is not None:
            self.__conn.disconnect()
            self.__conn = None

    @property
    def messenger(self):  # -> ClientMessenger:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver):
        self.__messenger = weakref.ref(transceiver)

    @property
    def facebook(self):  # -> ClientFacebook:
        return self.messenger.facebook

    #
    #   Handshake
    #
    def handshake(self, session: Optional[str] = None):
        user = self.facebook.current_user
        assert isinstance(user, User), 'current user not set yet'
        cmd = HandshakeCommand.start(session=session)
        env = Envelope.create(sender=user.identifier, receiver=self.identifier)
        i_msg = InstantMessage.create(head=env, body=cmd)
        s_msg = self.messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to handshake with server: %s' % self.identifier
        r_msg = self.messenger.sign_message(msg=s_msg)
        assert isinstance(r_msg, ReliableMessage), 'failed to sign message as user: %s' % user.identifier
        # carry meta, visa for first handshaking
        r_msg.meta = user.meta
        r_msg.visa = user.visa
        data = self.messenger.serialize_message(msg=r_msg)
        # send out directly
        self.messenger.send_package(data=data, handler=None)

    def handshake_success(self):
        user = self.facebook.current_user
        self.info('handshake success: %s' % user.identifier)
        from ..messenger import ClientMessenger
        messenger = self.messenger
        assert isinstance(messenger, ClientMessenger)
        messenger.handshake_accepted(server=self)

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        """ Send out a data package onto network """
        # pack
        pack = data + self.__conn.BOUNDARY
        # send
        error = self.__conn.send(data=pack)
        if handler is not None:
            if error is None:
                handler.success()
            else:
                handler.failed(error=error)
        return error is None

    def upload_data(self, data: bytes, msg: InstantMessage) -> str:
        """ Upload encrypted data to CDN """
        pass

    def download_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        """ Download encrypted data from CDN, and decrypt it when finished """
        pass


class ServerDelegate:

    @abstractmethod
    def handshake_accepted(self, server: Server):
        """
        Callback for handshake accepted

        :param server: current station
        """
        pass
