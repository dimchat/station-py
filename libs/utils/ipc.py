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
from typing import TypeVar, Generic, Optional, Any, Tuple, List

from ipx import SharedMemoryArrow
from startrek.fsm import Runner


class ArrowDelegate(ABC):

    @abstractmethod
    def arrow_received(self, obj: Any, arrow: SharedMemoryArrow):
        """ callback when received something from the arrow """
        raise NotImplementedError


class AutoArrow(Runner, ABC):

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    def __init__(self, name: str):
        super().__init__()
        self._arrow = SharedMemoryArrow.new(size=self.SHM_SIZE, name=name)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        return self


class IncomeArrow(AutoArrow):
    """ auto receiving """

    def __init__(self, name: str, delegate: ArrowDelegate):
        super().__init__(name=name)
        self.__delegate = weakref.ref(delegate)

    @property
    def delegate(self) -> ArrowDelegate:
        return self.__delegate()

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self._arrow.receive()
            if obj is not None:
                self.delegate.arrow_received(obj=obj, arrow=self._arrow)
                return True
        except Exception as error:
            print('[IPC] failed to process received object: %s, %s' % (obj, error))


class OutgoArrow(AutoArrow):
    """ auto sending """

    def __init__(self, name: str):
        super().__init__(name=name)
        self.__lock = threading.Lock()

    def send(self, obj: Optional[Any]) -> int:
        """ return -1 on failed """
        with self.__lock:
            try:
                return self._arrow.send(obj=obj)
            except Exception as error:
                print('[IPC] failed to send: %s, %s' % (obj, error))
                return -1

    # Override
    def process(self) -> bool:
        # send None to drive the arrow to resent delay objects
        self.send(obj=None)
        return False


T = TypeVar('T')


class ShuttleBus(Runner, ArrowDelegate, Generic[T]):

    def __init__(self):
        super().__init__()
        self.__income_arrow: Optional[IncomeArrow] = None
        self.__outgo_arrow: Optional[OutgoArrow] = None
        # caches
        self.__incomes: List[T] = []
        self.__outgoes: List[T] = []
        self.__income_lock = threading.Lock()
        self.__outgo_lock = threading.Lock()

    def set_arrows(self, arrows: Tuple[IncomeArrow, OutgoArrow]):
        self.__income_arrow = arrows[0]
        self.__outgo_arrow = arrows[1]

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        return self

    def __next(self) -> Optional[T]:
        """ get first outgo object from the waiting queue """
        with self.__outgo_lock:
            if len(self.__outgoes) > 0:
                return self.__outgoes.pop(0)

    def __push(self, obj):
        """ put outgo object back to the front of the waiting queue """
        with self.__outgo_lock:
            self.__outgoes.insert(0, obj)

    def send(self, obj: T):
        """ Put the obj in a waiting queue for sending out """
        with self.__outgo_lock:
            self.__outgoes.append(obj)

    def receive(self) -> Optional[T]:
        """ Get an obj from a waiting queue for received object """
        with self.__income_lock:
            if len(self.__incomes) > 0:
                return self.__incomes.pop(0)

    # Override
    def arrow_received(self, obj: Any, arrow: SharedMemoryArrow):
        with self.__income_lock:
            self.__incomes.append(obj)

    # Override
    def process(self) -> bool:
        # process incoming tasks
        busy = self.__income_arrow.process()
        # process outgoing tasks
        obj = self.__next()
        if obj is None:
            # send None to drive the arrow to resent delay objects
            self.__outgo_arrow.send(obj=None)
            # nothing to send now, return False to have a rest
        elif self.__outgo_arrow.send(obj=obj) < 0:
            # failed, put it back to the front
            self.__push(obj=obj)
        else:
            # sent
            busy = True
        return busy


class SHM:
    """
        Station process IDs
        ~~~~~~~~~~~~~~~~~~~

            0 - main           router, filter, dispatcher
            1 - receptionist   handshake (offline messages), ...
            2 - archivist      search engine
            3 - pusher         notification (ios, android)
            7 - monitor        statistic, session
            8 - octopus        station bridge
    """

    RECEPTIONIST_KEY1 = '0x%X' % 0xD1350101  # A -> B
    RECEPTIONIST_KEY2 = '0x%X' % 0xD1350102  # B -> A

    ARCHIVIST_KEY1 = '0x%X' % 0xD1350201  # A -> B
    ARCHIVIST_KEY2 = '0x%X' % 0xD1350202  # B -> A

    PUSHER_KEY = "0x%X" % 0xD1350301  # A -> B

    MONITOR_KEY = "0x%X" % 0xD1350701  # A -> B

    OCTOPUS_KEY1 = '0x%X' % 0xD1350801  # A -> B
    OCTOPUS_KEY2 = '0x%X' % 0xD1350802  # B -> A


class ReceptionistArrows:
    """ arrows between router and receptionist """

    @classmethod
    def primary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for router
        return IncomeArrow(name=SHM.RECEPTIONIST_KEY2, delegate=delegate),\
               OutgoArrow(name=SHM.RECEPTIONIST_KEY1)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for receptionist
        return IncomeArrow(name=SHM.RECEPTIONIST_KEY1, delegate=delegate),\
               OutgoArrow(name=SHM.RECEPTIONIST_KEY2)


class ArchivistArrows:
    """ arrows between router and archivist """

    @classmethod
    def primary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for router
        return IncomeArrow(name=SHM.ARCHIVIST_KEY2, delegate=delegate),\
               OutgoArrow(name=SHM.ARCHIVIST_KEY1)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for archivist
        return IncomeArrow(name=SHM.ARCHIVIST_KEY1, delegate=delegate),\
               OutgoArrow(name=SHM.ARCHIVIST_KEY2)


class OctopusArrows:
    """ arrows between router and bridge """

    @classmethod
    def primary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for router
        return IncomeArrow(name=SHM.OCTOPUS_KEY2, delegate=delegate),\
               OutgoArrow(name=SHM.OCTOPUS_KEY1)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> (IncomeArrow, OutgoArrow):
        # arrows for octopus
        return IncomeArrow(name=SHM.OCTOPUS_KEY1, delegate=delegate),\
               OutgoArrow(name=SHM.OCTOPUS_KEY2)


class PushArrow:
    """ arrow from router(dispatcher) to pusher """

    @classmethod
    def primary(cls) -> OutgoArrow:
        # arrow for router(dispatcher)
        return OutgoArrow(name=SHM.PUSHER_KEY)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> IncomeArrow:
        # arrow for pusher
        return IncomeArrow(name=SHM.PUSHER_KEY, delegate=delegate)


class MonitorArrow:
    """ arrow from router(dispatcher) to monitor """

    @classmethod
    def primary(cls) -> OutgoArrow:
        # arrow for router(dispatcher)
        return OutgoArrow(name=SHM.MONITOR_KEY)

    @classmethod
    def secondary(cls, delegate: ArrowDelegate) -> IncomeArrow:
        # arrow for monitor
        return IncomeArrow(name=SHM.MONITOR_KEY, delegate=delegate)
