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

from typing import Optional

from dimp import ID, EVERYWHERE, User
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Command
from dimp import Processor

from ..utils import NotificationCenter
from ..common import NotificationNames
from ..common import CommonMessenger, CommonFacebook

from .session import Session, SessionServer
from .dispatcher import Dispatcher


g_session_server = SessionServer()
g_dispatcher = Dispatcher()
g_facebook = CommonFacebook()


class ServerMessenger(CommonMessenger):

    def __init__(self):
        super().__init__()
        from .filter import Filter
        self.__filter = Filter(messenger=self)

    @property
    def facebook(self) -> CommonFacebook:
        return g_facebook

    def _create_facebook(self) -> CommonFacebook:
        return g_facebook

    def _create_processor(self) -> Processor:
        from .processor import ServerProcessor
        return ServerProcessor(messenger=self)

    @property
    def dispatcher(self) -> Dispatcher:
        return g_dispatcher

    def deliver_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        # FIXME: check deliver permission
        res = self.__filter.check_deliver(msg=msg)
        if res is None:
            # delivering is allowed, call dispatcher to deliver this message
            res = self.dispatcher.deliver(msg=msg)
        # pack response
        if res is not None:
            if self.facebook.public_key_for_encryption(identifier=msg.sender) is None:
                self.info('waiting visa key for: %s' % msg.sender)
                return None
            user = self.facebook.current_user
            env = Envelope.create(sender=user.identifier, receiver=msg.sender)
            i_msg = InstantMessage.create(head=env, body=res)
            s_msg = self.encrypt_message(msg=i_msg)
            assert s_msg is not None, 'failed to respond to: %s' % msg.sender
            return self.sign_message(msg=s_msg)

    #
    #   Session
    #
    @property
    def session_server(self) -> SessionServer:
        return g_session_server

    def current_session(self, identifier: ID) -> Session:
        address = self.remote_address
        assert address is not None, 'client address not found: %s' % identifier
        return self.session_server.get_session(client_address=address)

    #
    #   Remote user
    #
    @property
    def remote_user(self) -> User:
        return self.get_context(key='remote_user')

    @property
    def remote_address(self):  # (IP, port)
        return self.get_context(key='remote_address')

    #
    #   Sending command
    #
    def _send_command(self, cmd: Command, receiver: Optional[ID] = None) -> bool:
        if receiver is None:
            receiver = ID.create(name='station', address=EVERYWHERE)
        station = self.get_context(key='station')
        if station is None:
            user = self.facebook.current_user
            if user is None:
                return False
            sender = user.identifier
        else:
            sender = station.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=cmd)
        s_msg = self.encrypt_message(msg=i_msg)
        if s_msg is None:
            # failed to encrypt message
            return False
        r_msg = self.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        r_msg.delegate = self
        self.dispatcher.deliver(msg=r_msg)
        return True

    #
    #   HandshakeDelegate
    #
    def handshake_accepted(self, session: Session):
        session.active = True
        sender = session.identifier
        session_key = session.key
        client_address = session.client_address
        user = self.facebook.user(identifier=sender)
        self.context['remote_user'] = user
        self.info('handshake accepted %s %s, %s' % (client_address, sender, session_key))
        # post notification: USER_LOGIN
        NotificationCenter().post(name=NotificationNames.USER_LOGIN, sender=self, info={
            'ID': sender,
            'client_address': client_address,
        })
