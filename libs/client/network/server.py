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

from dimp import ID, User, EVERYONE
from dimp import Envelope, InstantMessage, ReliableMessage
from dimsdk import HandshakeCommand
from dimsdk import Station

from ...utils import Logging
from ...network import Hub, Gate, GateStatus, DeparturePriority

from ...common import CommonMessenger, CommonFacebook
from ...common import MessengerDelegate, CompletionHandler
from ...common import BaseSession


class Session(BaseSession):

    # def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
    #     super().__init__(messenger=messenger, address=address, sock=sock)

    def setup(self):
        # self.active = True
        self._set_active(True)
        super().setup()

    def finish(self):
        # self.active = False
        self._set_active(False)
        super().finish()

    #
    #   GateDelegate
    #

    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            self.info('connection lost, reconnecting: remote = %s, local = %s' % (remote, local))
            hub = self.gate.hub
            assert isinstance(hub, Hub), 'hub error: %s' % hub
            hub.connect(remote=remote, local=local)
        elif current == GateStatus.READY:
            self.messenger.connected()
            # handshake
            delegate = self.messenger.delegate
            if isinstance(delegate, Server):
                delegate.handshake()


class Server(Station, MessengerDelegate, Logging):
    """
        Remote Station
        ~~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int = 9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.__session: Optional[Session] = None
        self.__messenger: Optional[weakref.ReferenceType] = None

    def connect(self) -> Session:
        if self.__session is None:
            session = Session(messenger=self.messenger, address=(self.host, self.port))
            session.start()
            self.__session = session
        return self.__session

    def disconnect(self):
        if self.__session is not None:
            self.__session.stop()
            self.__session = None

    @property
    def messenger(self) -> CommonMessenger:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = weakref.ref(transceiver)

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    #
    #   Handshake
    #
    def handshake(self, session: Optional[str] = None):
        user = self.facebook.current_user
        assert isinstance(user, User), 'current user not set yet'
        env = Envelope.create(sender=user.identifier, receiver=self.identifier)
        assert isinstance(env, Envelope), 'envelope error: %s' % env
        cmd = HandshakeCommand.start(session=session)
        # allow connect server without meta.js
        if self.facebook.public_key_for_encryption(identifier=self.identifier) is None:
            cmd.group = EVERYONE
        # pack message
        i_msg = InstantMessage.create(head=env, body=cmd)
        messenger = self.messenger
        s_msg = messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to handshake with server: %s' % self.identifier
        r_msg = messenger.sign_message(msg=s_msg)
        assert isinstance(r_msg, ReliableMessage), 'failed to sign message as user: %s' % user.identifier
        # carry meta, visa for first handshaking
        r_msg.meta = user.meta
        r_msg.visa = user.visa
        data = messenger.serialize_message(msg=r_msg)
        # send out directly
        self.info('shaking hands: %s -> %s' % (env.sender, env.receiver))
        # Urgent Command
        session = self.connect()
        session.send_payload(payload=data, priority=DeparturePriority.URGENT)

    def handshake_success(self):
        user = self.facebook.current_user
        self.info('handshake success: %s, onto station: %s' % (user.identifier, self.identifier))
        from ..messenger import ClientMessenger
        messenger = self.messenger
        assert isinstance(messenger, ClientMessenger)
        messenger.handshake_accepted(server=self)

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        """ Send out a data package onto network """
        session = self.connect()
        if session.send_payload(payload=data, priority=priority):
            if handler is not None:
                handler.success()
            return True
        else:
            if handler is not None:
                error = IOError('Server error: failed to send data package')
                handler.failed(error=error)
            return False

    def upload_data(self, data: bytes, msg: InstantMessage) -> Optional[str]:
        """ Upload encrypted data to CDN """
        self.info('upload %d bytes for: %s' % (len(data), msg.content))
        return None

    def download_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        """ Download encrypted data from CDN, and decrypt it when finished """
        self.info('download %s for: %s' % (url, msg.content))
        return None


class ServerDelegate:

    @abstractmethod
    def handshake_accepted(self, server: Server):
        """
        Callback for handshake accepted

        :param server: current station
        """
        pass
