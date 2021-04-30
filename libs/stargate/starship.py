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

from .ship import Ship, ShipDelegate


"""
    Star Ship
    ~~~~~~~~~

    Container carrying data package
"""


class StarShip(Ship):
    """ Star Ship carrying package to remote Star Gate """

    # retry
    EXPIRES = 120  # 2 minutes
    RETRIES = 2

    # priority
    URGENT = -1
    NORMAL = 0
    SLOWER = 1

    def __init__(self, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__()
        self.__priority = priority
        # retry
        self.__timestamp = 0
        self.__retries = -1
        # callback
        if delegate is None:
            self.__delegate = None
        else:
            self.__delegate = weakref.ref(delegate)

    @property
    def delegate(self) -> Optional[ShipDelegate]:
        """ Get handler for this Star Ship """
        if self.__delegate is not None:
            return self.__delegate()

    @property
    def priority(self) -> int:
        """ Get priority of this Star Ship """
        return self.__priority

    @property
    def time(self) -> int:
        """ Get last time of trying """
        return self.__timestamp

    @property
    def retries(self) -> int:
        """ Get count of retries """
        return self.__retries

    @property
    def expired(self) -> bool:
        """ Check whether retry too many times and no response """
        delta = int(time.time()) - self.time
        return delta > (self.EXPIRES * self.RETRIES * 2)

    def update(self):
        """ Update retries count and time """
        self.__timestamp = int(time.time())
        self.__retries += 1
        return self
