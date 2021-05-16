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

from typing import Optional

from dimp import NetworkType
from dimp import ReliableMessage

from ..common import msg_traced, is_broadcast_message
from ..common import CommonProcessor
from ..common import Database

from .session import SessionServer
from .messenger import ServerMessenger


g_session_server = SessionServer()
g_database = Database()


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
        station = messenger.dispatcher.station
        if msg_traced(msg=msg, node=station, append=True):
            self.info('cycled msg: %s in %s' % (station, msg.get('traces')))
            if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
                self.warning('ignore station msg: %s -> %s' % (sender, receiver))
                return None
            if is_broadcast_message(msg=msg):
                self.warning('ignore traced broadcast msg: %s in %s' % (station, msg.get('traces')))
                return None
            sessions = g_session_server.active_sessions(identifier=receiver)
            if len(sessions) > 0:
                self.info('deliver cycled msg: %s, %s -> %s' % (station, sender, receiver))
                return messenger.deliver_message(msg=msg)
            else:
                self.info('store cycled msg: %s, %s -> %s' % (station, sender, receiver))
                g_database.store_message(msg=msg)
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
            return messenger.deliver_message(msg=msg)
        elif receiver.type != NetworkType.STATION:
            # receiver not station, deliver it
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
                # if this message sent to 'station@anywhere', or with group ID 'station@everywhere',
                # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
                # so respond them as message attachments.
                user = self.facebook.user(identifier=res.sender)
                res.meta = user.meta
                res.visa = user.visa
            return res
