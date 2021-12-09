# -*- coding: utf-8 -*-
#
#   IPC: Inter-Process Communication
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

import threading
import weakref
from abc import ABC, abstractmethod
from typing import Any, Optional

from ipx import SharedMemoryArrow

from startrek.fsm import Runner


class ArrowDelegate(ABC):

    @abstractmethod
    def arrow_received(self, obj: Any, arrow: SharedMemoryArrow):
        """ callback when received something from the arrow """
        raise NotImplementedError


class IncomeArrow(Runner):
    """ auto receiving """

    def __init__(self, size: int, name: str, delegate: ArrowDelegate):
        super().__init__()
        self.__arrow = SharedMemoryArrow.new(size=size, name=name)
        self.__delegate = weakref.ref(delegate)
        threading.Thread(target=self.run, daemon=True).start()

    @property
    def delegate(self) -> ArrowDelegate:
        return self.__delegate()

    def __try_receive(self) -> Optional[Any]:
        try:
            return self.__arrow.receive()
        except Exception as error:
            print('[IPC] receive error: %s' % error)

    # Override
    def process(self) -> bool:
        obj = self.__try_receive()
        if obj is None:
            # received nothing
            return False
        try:
            self.delegate.arrow_received(obj=obj, arrow=self.__arrow)
            return True
        except Exception as error:
            print('[IPC] failed to process received object: %s, %s' % (obj, error))


class OutgoArrow(Runner):
    """ auto sending """

    def __init__(self, size: int, name: str):
        super().__init__()
        self.__arrow = SharedMemoryArrow.new(size=size, name=name)
        self.__lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True).start()

    def __try_send(self, obj: Any) -> int:
        try:
            return self.__arrow.send(obj=obj)
        except Exception as error:
            print('[IPC] failed to send: %s, %s' % (obj, error))

    def send(self, obj: Any) -> int:
        with self.__lock:
            return self.__try_send(obj=obj)

    # Override
    def process(self) -> bool:
        self.send(obj=None)
        return False


"""
    Station process IDs
    ~~~~~~~~~~~~~~~~~~~
    
        0 - dispatcher     router (main)
        1 - receptionist   login session, offline messages
        2 - archivist      meta, document, search engine
        3 - pusher         notification (ios, android)
        7 - monitor        statistic, session
"""


class SessionArrows:
    """ arrows between dispatcher and receptionist """

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    SHM_KEY1 = "0xD1350101"  # A -> B
    SHM_KEY2 = "0xD1350102"  # B -> A

    @classmethod
    def primary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY2, delegate=delegate),\
               OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY1)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY1, delegate=delegate),\
               OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY2)


class SearchArrows:
    """ arrows between dispatcher and archivist """

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    SHM_KEY1 = "0xD1350201"  # A -> B
    SHM_KEY2 = "0xD1350202"  # B -> A

    @classmethod
    def primary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY2, delegate=delegate),\
               OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY1)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY1, delegate=delegate),\
               OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY2)


class PushArrow:
    """ arrow from dispatcher to pusher """

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    SHM_KEY = "0xD1350301"  # A -> B

    @classmethod
    def primary(cls) -> OutgoArrow:
        return OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> IncomeArrow:
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY, delegate=delegate)


class MonitorArrow:
    """ arrow from dispatcher to monitor """

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    SHM_KEY = "0xD1350701"  # A -> B

    @classmethod
    def primary(cls) -> OutgoArrow:
        return OutgoArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> IncomeArrow:
        return IncomeArrow(size=cls.SHM_SIZE, name=cls.SHM_KEY, delegate=delegate)
