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

from typing import Optional, Union, List

from startrek import ShipDelegate, StarGate
from startrek import Arrival, Departure, DeparturePriority

from udp.ba import ByteArray, Data
from udp.mtp import DataType, TransactionID, Header, Package
from udp import PackageArrival, PackageDeparture, PackageDocker


class PackUtils:

    @classmethod
    def parse_head(cls, data: Union[bytes, ByteArray]) -> Optional[Header]:
        if not isinstance(data, ByteArray):
            data = Data(buffer=data)
        return Header.parse(data=data)

    @classmethod
    def parse(cls, data: Union[bytes, ByteArray]) -> Optional[Package]:
        if not isinstance(data, ByteArray):
            data = Data(buffer=data)
        return Package.parse(data=data)

    @classmethod
    def create_command(cls, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.COMMAND,
                           body_length=body.size, body=body)

    @classmethod
    def create_message(cls, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.MESSAGE,
                           body_length=body.size, body=body)

    @classmethod
    def respond_command(cls, sn: TransactionID, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.COMMAND_RESPONSE,
                           sn=sn, body_length=body.size, body=body)

    @classmethod
    def respond_message(cls, sn: TransactionID, pages: int, index: int, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.MESSAGE_RESPONSE,
                           sn=sn, pages=pages, index=index, body_length=body.size, body=body)


""" MTP Stream Arrival Ship """
MTPStreamArrival = PackageArrival


class MTPStreamDeparture(PackageDeparture):
    """ MTP Stream Departure Ship """

    # Override
    def _split_package(self, pack: Package) -> List[Package]:
        # stream docker will not separate packages
        return [pack]


class MTPStreamDocker(PackageDocker):
    """ Docker for MTP packages """

    MAX_HEAD_LENGTH = 24

    def __init__(self, remote: tuple, local: Optional[tuple], gate: StarGate):
        super().__init__(remote=remote, local=local, gate=gate)
        self.__chunks = Data.ZERO
        self.__processing = 0

    # Override
    def _parse_package(self, data: Optional[bytes]) -> Optional[Package]:
        self.__processing += 1
        if self.__processing > 1:
            # it's already in processing now,
            # append the data to the tail of memory cache
            if data is not None and len(data) > 0:
                # assert isinstance(self.__chunks, ByteArray)
                self.__chunks = self.__chunks.concat(data)
            self.__processing -= 1
            return None
        # append the data to the memory cache
        if data is not None and len(data) > 0:
            buffer = self.__chunks.concat(data)
        else:
            buffer = self.__chunks
        self.__chunks = Data.ZERO
        assert isinstance(buffer, ByteArray)
        # check header
        head = PackUtils.parse_head(data=buffer)
        if head is None:
            # header error, seeking for next header
            pos = buffer.find(Header.MAGIC_CODE, start=1)
            if pos > 0:
                # found, drop all data before it
                buffer = buffer.slice(start=pos)
                if buffer.size > 0:
                    # join to the memory cache
                    if self.__chunks.size > 0:
                        self.__chunks = buffer.concat(self.__chunks)
                    else:
                        self.__chunks = buffer
                if self.__chunks.size > 0:
                    # try again
                    self.__processing -= 1
                    return self._parse_package(data=None)
            # waiting for more data
            self.__processing -= 1
            return None
        # header ok, check body length
        data_len = buffer.size
        head_len = head.size
        body_len = head.body_length
        if body_len == -1:
            pack_len = data_len
        else:
            pack_len = head_len + body_len
        if data_len > pack_len:
            # cut the tail and put it back to the memory cache
            if self.__chunks.size > 0:
                self.__chunks = buffer.slice(start=pack_len).concat(self.__chunks)
            else:
                self.__chunks = buffer.slice(start=pack_len)
            buffer = buffer.slice(start=0, end=pack_len)
        # OK
        self.__processing -= 1
        return Package(data=buffer, head=head, body=buffer.slice(start=head_len))

    # Override
    def _create_arrival(self, pack: Package) -> Arrival:
        return MTPStreamArrival(pack=pack)

    # Override
    def _create_departure(self, pack: Package, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> Departure:
        return MTPStreamDeparture(pack=pack, priority=priority, delegate=delegate)

    # Override
    def _respond_command(self, sn: TransactionID, body: bytes):
        pack = PackUtils.respond_command(sn=sn, body=body)
        self.send_package(pack=pack)

    # Override
    def _respond_message(self, sn: TransactionID, pages: int, index: int):
        pack = PackUtils.respond_message(sn=sn, pages=pages, index=index, body=OK)
        self.send_package(pack=pack)

    # Override
    def pack(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> Departure:
        pkg = PackUtils.create_message(body=payload)
        return self._create_departure(pack=pkg, priority=priority, delegate=delegate)

    # Override
    def heartbeat(self):
        pkg = PackUtils.create_command(body=PING)
        outgo = self._create_departure(pack=pkg, priority=DeparturePriority.SLOWER)
        self.append_departure(ship=outgo)

    @classmethod
    def check(cls, advance_party: List[bytes]) -> bool:
        if advance_party is None:
            count = 0
        else:
            count = len(advance_party)
        if count == 0:
            return False
        elif count == 1:
            data = Data(buffer=advance_party[0])
        else:
            data = Data(buffer=advance_party[0])
            for i in range(1, count):
                data = data.concat(advance_party[i])
        head = PackUtils.parse_head(data=data)
        return head is not None


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
AGAIN = b'AGAIN'
