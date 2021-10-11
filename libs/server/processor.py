# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Server extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import time
from typing import Optional

from dimp import NetworkType
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimsdk import ReceiptCommand, HandshakeCommand

from ..database import Database
from ..common import msg_traced, is_broadcast_message
from ..common import CommonProcessor

from .session import SessionServer
from .messenger import ServerMessenger
from .dispatcher import Dispatcher


g_database = Database()
g_session_server = SessionServer()
g_dispatcher = Dispatcher()


class ServerProcessor(CommonProcessor):

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        messenger = self.messenger
        sender = msg.sender
        receiver = msg.receiver
        #
        # 1. verify message
        #
        s_msg = messenger.verify_message(msg=msg)
        if s_msg is None:
            self.error('failed to verify message: %s -> %s' % (sender, receiver))
            # waiting for sender's meta if not exists
            return None
        # 1.1. check traces
        station = g_dispatcher.station
        if msg_traced(msg=msg, node=station, append=True):
            sig = msg.get('signature')
            if sig is not None and len(sig) > 8:
                sig = sig[-8:]
            self.info('cycled msg [%s]: %s in %s' % (sig, station, msg.get('traces')))
            if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
                self.warning('ignore station msg [%s]: %s -> %s' % (sig, sender, receiver))
                return None
            if is_broadcast_message(msg=msg):
                self.warning('ignore traced broadcast msg [%s]: %s -> %s' % (sig, sender, receiver))
                return None
            sessions = g_session_server.active_sessions(identifier=receiver)
            if len(sessions) > 0:
                self.info('deliver cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                g_database.save_message(msg=msg)
                return messenger.deliver_message(msg=msg)
            else:
                self.info('store cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                g_database.save_message(msg=msg)
                return None
        # 1.2. check broadcast/group message
        if receiver.is_broadcast:
            res = messenger.deliver_message(msg=msg)
            # if this is a broadcast, deliver it, send back the response
            # and continue to process it with the station.
            # because this station is also a recipient too.
            if res is not None:
                messenger.send_message(msg=res, priority=1)
        elif receiver.is_group:
            # or, if this is is an ordinary group message,
            # just deliver it to the group assistant
            # and return the response to the sender.
            g_database.save_message(msg=msg)
            return messenger.deliver_message(msg=msg)
        elif receiver.type != NetworkType.STATION:
            # receiver not station, deliver it
            g_database.save_message(msg=msg)
            return messenger.deliver_message(msg=msg)
        #
        # 2. process message
        #
        try:
            s_msg = messenger.process_secure_message(msg=s_msg, r_msg=msg)
            if s_msg is None:
                # nothing to respond
                return None
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                g_database.save_message(msg=msg)
                return messenger.deliver_message(msg=msg)
            else:
                raise error
        #
        # 3. sign message
        #
        res = messenger.sign_message(msg=s_msg)
        if res is not None:
            group = msg.group
            if receiver == 'station@anywhere' or (group is not None and group.is_broadcast):
                # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
                # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
                # so respond them as message attachments.
                user = self.facebook.user(identifier=res.sender)
                res.meta = user.meta
                res.visa = user.visa
            return res

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> Optional[Content]:
        # check login before process content
        messenger = self.messenger
        session = messenger.current_session
        if session.identifier is None or not session.active:
            if not isinstance(content, HandshakeCommand):
                # handshake first
                messenger.suspend_message(msg=r_msg)
                return HandshakeCommand.ask(session=session.key)
        # now process content
        res = super().process_content(content=content, r_msg=r_msg)
        if res is None:
            # respond nothing
            return None
        elif isinstance(res, ReceiptCommand):
            sender = r_msg.sender
            if sender.type == NetworkType.STATION:
                # no need to respond receipt to station
                when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                self.info('drop receipt responding to %s, origin msg time=[%s]' % (sender, when))
                return None
        elif isinstance(res, TextContent):
            sender = r_msg.sender
            if sender.type == NetworkType.STATION:
                # no need to respond text message to station
                when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                self.info('drop text msg responding to %s, origin time=[%s], text=%s' % (sender, when, res.text))
                return None
        # OK
        return res
