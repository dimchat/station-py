# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

import threading
import time
from typing import Dict

from dimples import ReliableMessage

from ..utils import Singleton


class SigPool:
    """ Signature pool for messages """

    EXPIRES = 3600 * 5

    def __init__(self):
        super().__init__()
        self._next_time = 0
        self.__caches: Dict[str, float] = {}  # str(msg.signature) => timestamp

    def purge(self, now: float):
        """ remove expired traces """
        if now < self._next_time:
            return False
        expired = now - self.EXPIRES
        keys = set(self.__caches.keys())
        for sig in keys:
            msg_time = self.__caches.get(sig)
            if msg_time is None or msg_time < expired:
                self.__caches.pop(sig, None)
        # purge it next hour
        self._next_time = now + 3600
        return True

    def duplicated(self, msg: ReliableMessage) -> bool:
        """ check whether duplicated """
        sig = msg['signature']
        cached = self.__caches.get(sig)
        if cached is None:
            # cache not found, create a new one with message time
            when = msg.time
            self.__caches[sig] = when
            return False
        else:
            return True


class LockedPool(SigPool):

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()

    # Override
    def purge(self, now: float):
        if now < self._next_time:
            # we can treat the msg.time as real time for initial checking
            return False
        # if message time out, check with real time
        now = time.time()
        with self.__lock:
            super().purge(now=now)

    # Override
    def duplicated(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            return super().duplicated(msg=msg)


@Singleton
class Checkpoint:
    """ Check for duplicate messages """

    def __init__(self):
        super().__init__()
        self.__pool = LockedPool()

    def duplicated(self, msg: ReliableMessage) -> bool:
        pool = self.__pool
        repeated = pool.duplicated(msg=msg)
        pool.purge(now=msg.time)
        return repeated
