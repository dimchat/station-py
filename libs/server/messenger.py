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

from dimp import NetworkType, ID
from dimp import Envelope, InstantMessage, SecureMessage, ReliableMessage
from dimp import Command
from dimp import Processor

from ..utils import get_msg_sig
from ..utils import NotificationCenter
from ..database import Database
from ..common import msg_traced, is_broadcast_message
from ..common import NotificationNames
from ..common import CommonMessenger

from .session import Session, SessionServer
from .dispatcher import Dispatcher


g_database = Database()
g_session_server = SessionServer()


class ServerMessenger(CommonMessenger):

    def __init__(self):
        super().__init__()
        from .filter import Filter
        self.__filter = Filter(messenger=self)
        self.__session: Optional[Session] = None

    def _create_processor(self) -> Processor:
        from .processor import ServerProcessor
        return ServerProcessor(facebook=self.facebook, messenger=self)

    def __deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        # FIXME: check deliver permission
        res = self.__filter.check_deliver(msg=msg)
        if res is None:
            # delivering is allowed, call dispatcher to deliver this message
            g_database.save_message(msg=msg)
            res = Dispatcher().deliver(msg=msg)
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
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        sender = msg.sender
        receiver = msg.receiver
        # 1.1. check traces
        current = self.facebook.current_user
        sid = current.identifier
        if msg_traced(msg=msg, node=sid, append=True):
            sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
            self.info('cycled msg [%s]: %s in %s' % (sig, sid, msg.get('traces')))
            if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
                self.warning('ignore station msg [%s]: %s -> %s' % (sig, sender, receiver))
                return []
            if is_broadcast_message(msg=msg):
                self.warning('ignore traced broadcast msg [%s]: %s -> %s' % (sig, sender, receiver))
                return []
            sessions = g_session_server.active_sessions(identifier=receiver)
            if len(sessions) > 0:
                self.info('deliver cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                return self.__deliver_message(msg=msg)
            else:
                self.info('store cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                g_database.save_message(msg=msg)
                return []
        # 1.2. check broadcast/group message
        deliver_responses = []
        if receiver.is_broadcast:
            deliver_responses = self.__deliver_message(msg=msg)
            # if this is a broadcast, deliver it, send back the response
            # and continue to process it with the station.
            # because this station is also a recipient too.
        elif receiver.is_group:
            # or, if this is is an ordinary group message,
            # just deliver it to the group assistant
            # and return the response to the sender.
            return self.__deliver_message(msg=msg)
        elif receiver.type != NetworkType.STATION:
            # receiver not station, deliver it
            return self.__deliver_message(msg=msg)
        # call super
        try:
            responses = super().process_reliable_message(msg=msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                return self.__deliver_message(msg=msg)
            else:
                raise error
        if len(responses) == 0:
            return deliver_responses
        # check for first login
        group = msg.group
        if receiver == 'station@anywhere' or (group is not None and group.is_broadcast):
            # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
            # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
            # so respond them as message attachments.
            user = self.facebook.current_user
            for res in responses:
                res.meta = user.meta
                res.visa = user.visa
        # check response for delivering broadcast message
        if len(deliver_responses) > 0:
            for res in deliver_responses:
                responses.append(res)
        return responses

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if self.__trusted_sender(sender=msg.sender):
            self.debug('skip verifying message: %s -> %s' % (msg.sender, msg.receiver))
            # FIXME: if stream hijacking occurs?
            return msg
        else:
            self.debug('try verifying message: %s -> %s' % (msg.sender, msg.receiver))
            return super().verify_message(msg=msg)

    def __trusted_sender(self, sender: ID) -> bool:
        current = self.current_id
        if current is None:
            # not login yet
            return False
        # handshake accepted, check current user with sender
        if current == sender:
            # no need to verify signature of this message
            # which sender is equal to current id in session
            return True
        # if current.type == NetworkType.STATION:
        #     # if it's a roaming message delivered from another neighbor station,
        #     # shall we trust that neighbor totally and skip verifying too ???
        #     return True

    #
    #   Session
    #
    @property
    def session(self) -> Session:
        return self.__session

    @session.setter
    def session(self, session: Session):
        self.__session = session

    @property
    def current_id(self) -> Optional[ID]:
        session = self.__session
        if session is not None:
            return session.identifier

    #
    #   Sending command
    #
    def send_command(self, cmd: Command, priority: int, receiver: Optional[ID] = None) -> bool:
        if receiver is None:
            receiver = ID.parse(identifier='stations@everywhere')
        srv = self.facebook.current_user
        return self.send_content(sender=srv.identifier, receiver=receiver, content=cmd, priority=priority)

    # Override
    def handshake_accepted(self, identifier: ID, client_address: tuple = None):
        station = self.facebook.current_user
        sid = station.identifier
        now = int(time.time())
        self.info('handshake accepted %s: %s' % (client_address, identifier))
        # post notification: USER_LOGIN
        NotificationCenter().post(name=NotificationNames.USER_LOGIN, sender=self, info={
            'ID': str(identifier),
            'client_address': client_address,
            'station': str(sid),
            'time': now,
        })
