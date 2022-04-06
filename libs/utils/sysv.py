# -*- coding: utf-8 -*-
#
#   SHM: Shared Memory
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

from typing import Union, Optional

import sysv_ipc  # 'sysv-ipc'==1.1.0

from ipx import GiantQueue
from ipx import SharedMemory
from ipx import SharedMemoryController


def create_shared_memory(size: int, key: int) -> sysv_ipc.SharedMemory:
    return sysv_ipc.SharedMemory(key=key, flags=sysv_ipc.IPC_CREAT, mode=SysvSharedMemory.MODE, size=size)


class SysvSharedMemory(SharedMemory):

    MODE = 0o644

    def __init__(self, size: int, key: int):
        super().__init__()
        self.__shm = create_shared_memory(size=size, key=key)

    @property
    def shm(self) -> sysv_ipc.SharedMemory:
        return self.__shm

    @property
    def id(self) -> int:
        return self.shm.id

    @property
    def key(self) -> int:
        return self.shm.key

    @property
    def mode(self) -> int:
        return self.shm.mode

    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        buffer = self._buffer_to_string()
        return '<%s id=%d key=0x%08x mode=%o size=%d>\n%s\n</%s "%s">'\
               % (cname, self.id, self.key, self.mode, self.size, buffer, cname, mod)

    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        buffer = self._buffer_to_string()
        return '<%s id=%d key=0x%08x mode=%o size=%d>\n%s\n</%s "%s">'\
               % (cname, self.id, self.key, self.mode, self.size, buffer, cname, mod)

    @property  # Override
    def size(self) -> int:
        return self.shm.size

    # Override
    def detach(self):
        self.shm.detach()

    # Override
    def destroy(self):
        self.shm.remove()

    # Override
    def get_byte(self, index: int) -> int:
        data = self.shm.read(1, offset=index)
        return data[0]

    # Override
    def get_bytes(self, start: int = 0, end: int = None) -> Optional[bytes]:
        if end is None:
            end = self.size
        if 0 <= start < end <= self.size:
            return self.shm.read(end - start, offset=start)

    # Override
    def set_byte(self, index: int, value: int):
        data = bytearray(1)
        data[0] = value
        self.shm.write(data, offset=index)

    # Override
    def update(self, index: int, source: Union[bytes, bytearray], start: int = 0, end: int = None):
        src_len = len(source)
        if end is None:
            end = src_len
        if start < end:
            if 0 < start or end < src_len:
                source = source[start:end]
            self.shm.write(source, offset=index)


class SysvSharedMemoryController(SharedMemoryController):

    @classmethod
    def new(cls, size: int, name: str = None, key: int = 0):
        if key == 0:
            pos = name.index('0x') + 2
            key = int(name[pos:], 16)
        shm = SysvSharedMemory(size=size, key=key)
        queue = GiantQueue(memory=shm)
        return cls(queue=queue)
