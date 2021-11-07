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

import socket
import weakref
from typing import Optional

from dimp import ID, User, EVERYONE
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Command
from dimsdk import HandshakeCommand
from dimsdk import Station

from startrek.fsm import StateDelegate

from ...utils import Logging
from ...network import Hub, Gate, GateStatus, DeparturePriority
from ...network import TCPClientGate

from ...common import CommonMessenger, CommonFacebook
from ...common import MessengerDelegate, CompletionHandler
from ...common import BaseSession


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__(messenger=messenger, address=address, sock=sock)
        self.__key: Optional[str] = None

    @property
    def key(self) -> Optional[str]:
        return self.__key

    @key.setter
    def key(self, session: str):
        self.__key = session

    def setup(self):
        self.active = True
        super().setup()

    def finish(self):
        self.active = False
        super().finish()

    #
    #   GateDelegate
    #

    # Override
    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            self.info('connection lost, reconnecting: remote = %s, local = %s' % (remote, local))
            hub = self.gate.hub
            assert isinstance(hub, Hub), 'hub error: %s' % hub
            hub.connect(remote=remote, local=local)
        elif current == GateStatus.READY:
            # handshake
            messenger = self.messenger
            assert isinstance(messenger, CommonMessenger)
            delegate = messenger.delegate
            if isinstance(delegate, Server):
                delegate.handshake(session_key=None)


class Server(Station, MessengerDelegate, StateDelegate, Logging):
    """
        Remote Station
        ~~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int = 9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.__messenger: Optional[weakref.ReferenceType] = None
        self.__session: Optional[Session] = None
        self.__current_user: Optional[User] = None
        self.__fsm = self._create_state_machine()

    def _create_state_machine(self):
        from .state import StateMachine
        fsm = StateMachine(server=self)
        fsm.start()
        return fsm

    @property
    def current_state(self):
        return self.__fsm.current_state

    @property
    def status(self):
        session = self.connect()
        gate = session.gate
        assert isinstance(gate, TCPClientGate)
        return gate.gate_status(remote=gate.remote_address, local=None)

    @property
    def current_user(self) -> Optional[User]:
        return self.__current_user

    @current_user.setter
    def current_user(self, user: User):
        if user != self.__current_user:
            self.__current_user = user
            # switch state for re-login
            self.__fsm.session_key = None

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
    def session_key(self) -> Optional[str]:
        session = self.__session
        if session is not None:
            return session.key

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

    def __pack(self, cmd: Command) -> ReliableMessage:
        user = self.current_user
        assert user is not None, 'current user not set'
        uid = user.identifier
        sid = self.identifier
        env = Envelope.create(sender=uid, receiver=sid)
        # allow connect server without meta.js
        facebook = self.facebook
        if facebook.public_key_for_encryption(identifier=sid) is None:
            cmd.group = EVERYONE
        # pack message
        i_msg = InstantMessage.create(head=env, body=cmd)
        messenger = self.messenger
        s_msg = messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to encrypt message: %s' % i_msg
        r_msg = messenger.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        return r_msg

    #
    #   Handshake
    #
    def handshake(self, session_key: Optional[str] = None):
        user = self.current_user
        if user is None:
            # current user not set yet
            return
        # check FSM state == 'Handshaking'
        from .state import ServerState
        current_state = self.current_state
        assert isinstance(current_state, ServerState), 'current state error: %s' % current_state
        if current_state.name not in [ServerState.HANDSHAKING, ServerState.CONNECTED, ServerState.RUNNING]:
            # FIXME: sometimes the connection state will be reset
            self.error('server state not for handshaking: %s' % current_state)
            return
        # check connection status = 'Connected'
        status = self.status
        if status != GateStatus.READY:
            # FIXME: sometimes the connection will be lost while handshaking
            self.error('server not connected')
            return
        session = self.connect()
        if session_key is not None:
            session.key = session_key
        self.__fsm.session_key = None
        self.info('shaking hands with session key: %s, id=%s' % (self.session_key, self.identifier))
        # create handshake command
        cmd = HandshakeCommand.start(session=session_key)
        # TODO: set last received message time
        r_msg = self.__pack(cmd=cmd)
        # carry meta, visa for first handshaking
        r_msg.meta = user.meta
        r_msg.visa = user.visa
        data = self.messenger.serialize_message(msg=r_msg)
        # send out directly
        self.info('shaking hands: %s -> %s' % (r_msg.sender, r_msg.receiver))
        # Urgent Command
        session.send_payload(payload=data, priority=DeparturePriority.URGENT)

    def handshake_success(self):
        # check FSM state == 'Handshaking'
        from .state import ServerState
        state = self.current_state
        if state != ServerState.HANDSHAKING:
            # FIXME: sometimes the connection state will be reset
            self.error('server state not handshaking: %s' % state)
        user = self.current_user
        self.info('handshake success: %s, onto station: %s' % (user.identifier, self.identifier))
        session_key = self.session_key
        self.__fsm.session_key = session_key
        self.messenger.handshake_accepted(identifier=user.identifier)

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

    #
    #   State Delegate
    #

    def enter_state(self, state, ctx):
        # called before state changed
        pass

    def exit_state(self, state, ctx):
        # called after state changed
        from .state import StateMachine, ServerState
        assert isinstance(ctx, StateMachine), 'server state machine error: %s' % ctx
        current = ctx.current_state
        self.info('server state changed: %s -> %s, id=%s' % (state, current, self.identifier))
        if current is None:
            return
        # TODO: post notification 'server_state_changed'
        if current == ServerState.HANDSHAKING:
            # start handshake
            self.handshake(session_key=None)

    def pause_state(self, state, ctx):
        pass

    def resume_state(self, state, ctx):
        # TODO: clear session key for re-login?
        pass
