# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
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

from abc import ABC, abstractmethod
from typing import Optional

from dimp import ID
from dimp import Content
from dimp import InstantMessage, ReliableMessage


class Transmitter(ABC):

    @abstractmethod
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content, priority: int) -> bool:
        """
        Send content from sender to receiver with priority

        :param sender:   from where
        :param receiver: to where
        :param content:  message content
        :param priority: smaller is faster
        :return: False on error
        """
        raise NotImplemented

    @abstractmethod
    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        raise NotImplemented

    @abstractmethod
    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        raise NotImplemented
