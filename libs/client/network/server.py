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

from tcp import ActiveConnection

from dimp import ID, User, EVERYONE
from dimp import Envelope, InstantMessage, ReliableMessage
from dimsdk import HandshakeCommand
from dimsdk import Station
from dimsdk import MessengerDelegate, CompletionHandler
from dimsdk.messenger import MessageCallback

from ...utils import Log
from ...stargate import GateStatus, ShipDelegate, StarShip
from ...stargate import MTPDocker
from ...common import CommonMessenger, CommonFacebook
from ...common import BaseSession


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, host: str, port: int):
        super().__init__(messenger=messenger, connection=ActiveConnection(address=(host, port)))
        self.__address = (host, port)
        self.gate.worker = MTPDocker(gate=self.gate)

    def setup(self):
        self.active = True
        super().setup()

    def finish(self):
        self.active = False
        super().finish()

    #
    #   GateDelegate
    #

    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        super().gate_status_changed(gate=gate, old_status=old_status, new_status=new_status)
        if new_status == GateStatus.Connected:
            delegate = self.messenger.delegate
            if isinstance(delegate, Server):
                delegate.handshake()


class Server(Station, MessengerDelegate):
    """
        Remote Station
        ~~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int = 9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.__session: Optional[Session] = None
        self.__messenger: Optional[weakref.ReferenceType] = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def connect(self):
        if self.__session is None:
            session = Session(messenger=self.messenger, host=self.host, port=self.port)
            session.start()
            self.__session = session

    def disconnect(self):
        if self.__session is not None:
            self.__session.stop()
            self.__session = None

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
        env = Envelope.create(sender=user.identifier, receiver=self.identifier)
        assert isinstance(env, Envelope), 'envelope error: %s' % env
        cmd = HandshakeCommand.start(session=session)
        # allow connect server without meta.js
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        if facebook.public_key_for_encryption(identifier=self.identifier) is None:
            cmd.group = EVERYONE
        # pack message
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
        self.info('shaking hands: %s -> %s' % (env.sender, env.receiver))
        # Urgent Command
        self.__session.send(payload=data, priority=StarShip.URGENT)

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
        delegate = None
        if isinstance(handler, MessageCallback):
            callback = handler.callback
            if isinstance(callback, ShipDelegate):
                delegate = callback
        if self.__session.send(payload=data, delegate=delegate):
            if handler is not None:
                handler.success()
            return True
        else:
            if handler is not None:
                error = IOError('Server error: failed to send data package')
                handler.failed(error=error)
            return False

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
