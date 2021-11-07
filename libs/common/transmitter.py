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
    Common extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimp import InstantMessage, ReliableMessage
from dimsdk import MessageTransmitter, Callback

from ..utils import Logging

from .messenger import CommonMessenger, CompletionHandler


class CommonTransmitter(MessageTransmitter, Logging):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    def send_instant_message(self, msg: InstantMessage,
                             callback: Optional[Callback] = None, priority: int = 0) -> bool:
        messenger = self.messenger
        # Send message (secured + certified) to target station
        s_msg = messenger.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            # raise AssertionError('failed to encrypt message: %s' % msg)
            return False
        r_msg = messenger.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set iMsg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        # TODO: if OK, set iMsg.state = sending; else set iMsg.state = waiting
        ok = messenger.send_reliable_message(msg=r_msg, callback=callback, priority=priority)
        # # save signature for receipt
        # msg['signature'] = r_msg.get('signature')
        if not messenger.save_message(msg=msg):
            return False
        return ok

    def send_reliable_message(self, msg: ReliableMessage,
                              callback: Optional[Callback] = None, priority: int = 0) -> bool:
        handler = MessageCallback(msg=msg, cb=callback)
        messenger = self.messenger
        data = messenger.serialize_message(msg=msg)
        return messenger.send_package(data=data, handler=handler, priority=priority)


class MessageCallback(CompletionHandler):

    def __init__(self, msg: ReliableMessage, cb: Callback):
        super().__init__()
        self.msg = msg
        self.callback = cb

    def success(self):
        callback = self.callback
        if callback is not None:
            callback.finished(msg=self.msg, error=None)

    def failed(self, error):
        callback = self.callback
        if callback is not None:
            callback.finished(msg=self.msg, error=error)
