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

import time
import weakref
from typing import Optional

from dmtp.mtp import Package

from .base import GateDelegate
from .base import OutgoShip


class StarShip(OutgoShip):

    def __init__(self, package: Package, priority: int = 0, delegate: Optional[GateDelegate] = None):
        super().__init__()
        self.__package = package
        self.__priority = priority
        if delegate is None:
            self.__delegate = None
        else:
            self.__delegate = weakref.ref(delegate)
        # retry
        self.__timestamp = 0
        self.__retries = -1

    # Override
    @property
    def delegate(self) -> Optional[GateDelegate]:
        """ Get request handler """
        if self.__delegate is not None:
            return self.__delegate()

    # Override
    @property
    def priority(self) -> int:
        return self.__priority

    # Override
    @property
    def time(self) -> int:
        return self.__timestamp

    # Override
    @property
    def retries(self) -> int:
        return self.__retries

    # Override
    def update(self):
        self.__timestamp = int(time.time())
        self.__retries += 1
        return self

    @property
    def package(self) -> Package:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def payload(self) -> bytes:
        return self.package.body.get_bytes()
