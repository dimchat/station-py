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
    Messenger
    ~~~~~~~~~

    Transform and send message
"""

from typing import Optional

from dimp import ID
from dimp import SecureMessage, ReliableMessage
from dimsdk import Messenger
from dkd import InstantMessage, Content


class CommonMessenger(Messenger):

    #
    #   Message
    #
    def broadcast_message(self, msg: ReliableMessage) -> Optional[Content]:
        # TODO: if this run in station, broadcast this message to everyone@everywhere
        pass

    def deliver_message(self, msg: ReliableMessage) -> Optional[Content]:
        # TODO: if this run in station, deliver this message to the receiver
        pass

    def save_message(self, msg: InstantMessage) -> bool:
        pass

    #
    #   Command
    #
    def query_meta(self, identifier: ID) -> bool:
        # TODO: if this run in client, query meta from the current station
        #       else query from neighbour stations
        pass

    #
    #   Transform
    #
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        try:
            return super().verify_message(msg=msg)
        except LookupError:
            # TODO: keep this message in waiting list for meta response
            return None
