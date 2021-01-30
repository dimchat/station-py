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

from dimp import ReliableMessage

from ..common import CommonProcessor

from .messenger import ServerMessenger
from .transmitter import ServerTransmitter


class ServerProcessor(CommonProcessor):

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def transmitter(self) -> ServerTransmitter:
        return self.messenger.transmitter

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = msg.receiver
        if receiver.is_group:
            # verify signature
            s_msg = self.messenger.verify_message(msg=msg)
            if s_msg is None:
                # signature error?
                return None
            # deliver group message
            res = self.transmitter.deliver_message(msg=msg)
            if receiver.is_broadcast:
                # if this is a broadcast, deliver it, send back the response
                # and continue to process it with the station.
                # because this station is also a recipient too.
                if res is not None:
                    self.messenger.send_message(msg=res)
            else:
                # or, this is is an ordinary group message,
                # just deliver it to the group assistant
                # and return the response to the sender.
                return res
        # try to decrypt and process message
        try:
            return super().process_reliable_message(msg=msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                return self.transmitter.deliver_message(msg=msg)
            else:
                raise error
