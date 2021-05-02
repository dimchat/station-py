# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
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

from abc import abstractmethod
from typing import Optional

from .ship import ShipDelegate
from .starship import StarShip


"""
    Star Worker
    ~~~~~~~~~~~

    Processor for Star Ships
"""


class Worker:
    """ Star Worker for packages in Ships """

    @abstractmethod
    def setup(self):
        """ Set up connection """
        raise NotImplemented

    @abstractmethod
    def handle(self):
        """ Call 'process()' circularly """
        raise NotImplemented

    @abstractmethod
    def process(self) -> bool:
        """ Process incoming/outgoing Ships """
        raise NotImplemented

    @abstractmethod
    def finish(self):
        """ Do clean jobs """
        raise NotImplemented

    @abstractmethod
    def pack(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> StarShip:
        """ Pack the payload to an outgo Ship """
        raise NotImplemented
