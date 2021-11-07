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
    Messenger for request handler in station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

import time
from typing import Optional, List

from dimp import ID
from dimp import Envelope, InstantMessage, SecureMessage, ReliableMessage
from dimp import Command
from dimp import Processor

from ..utils import NotificationCenter
from ..database import Database
from ..common import NotificationNames
from ..common import CommonMessenger

from .session import Session, SessionServer
from .dispatcher import Dispatcher


g_database = Database()
g_session_server = SessionServer()
g_dispatcher = Dispatcher()


class ServerMessenger(CommonMessenger):

    def __init__(self):
        super().__init__()
        from .filter import Filter
        self.__filter = Filter(messenger=self)
        self.__current_session: Optional[Session] = None

    def _create_processor(self) -> Processor:
        from .processor import ServerProcessor
        return ServerProcessor(messenger=self)

    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        # FIXME: check deliver permission
        res = self.__filter.check_deliver(msg=msg)
        if res is None:
            # delivering is allowed, call dispatcher to deliver this message
            g_database.save_message(msg=msg)
            res = g_dispatcher.deliver(msg=msg)
        # pack response
        if res is None:
            return []
        if self.facebook.public_key_for_encryption(identifier=msg.sender) is None:
            self.info('waiting visa key for: %s' % msg.sender)
            return []
        user = self.facebook.current_user
        env = Envelope.create(sender=user.identifier, receiver=msg.sender)
        i_msg = InstantMessage.create(head=env, body=res)
        s_msg = self.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to respond to: %s' % msg.sender
        r_msg = self.sign_message(msg=s_msg)
        return [r_msg]

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        session = self.current_session
        if session is not None and session.identifier == msg.sender:
            # handshake accepted, no need to verify signature of this message
            # which sender is equal to current session id
            self.debug('skip verifying message: %s -> %s, %s' % (msg.sender, msg.receiver, session))
            # FIXME: if stream hijacking occurs?
            return msg
        # TODO: if it's a roaming message delivered from another neighbor station?
        #       shall we trust that neighbor totally and skip verifying too?
        self.debug('verifying message: %s -> %s' % (msg.sender, msg.receiver))
        return super().verify_message(msg=msg)

    #
    #   Session
    #
    @property
    def current_session(self) -> Session:
        return self.__current_session

    @current_session.setter
    def current_session(self, session: Session):
        self.__current_session = session

    #
    #   Sending command
    #
    def _send_command(self, cmd: Command, receiver: Optional[ID] = None) -> bool:
        if receiver is None:
            receiver = ID.parse(identifier='stations@everywhere')
        srv = self.facebook.current_user
        env = Envelope.create(sender=srv.identifier, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=cmd)
        s_msg = self.encrypt_message(msg=i_msg)
        if s_msg is None:
            # failed to encrypt message
            return False
        r_msg = self.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        r_msg.delegate = self
        g_dispatcher.deliver(msg=r_msg)
        return True

    # Override
    def handshake_accepted(self, identifier: ID, client_address: tuple = None):
        sid = g_dispatcher.station
        now = int(time.time())
        self.info('handshake accepted %s: %s' % (client_address, identifier))
        # post notification: USER_LOGIN
        NotificationCenter().post(name=NotificationNames.USER_LOGIN, sender=self, info={
            'ID': identifier,
            'client_address': client_address,
            'station': sid,
            'time': now,
        })
