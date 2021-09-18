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

    MAGIC_CODE = Header.MAGIC_CODE
    MAGIC_CODE_OFFSET = 0

    MAX_HEAD_LENGTH = 24

    @classmethod
    def seek_header(cls, data: ByteArray) -> (Optional[Header], int):
        head = Header.parse(data=data)
        if head is not None:
            # got it (offset = 0)
            return head, 0
        data_len = data.size
        if data_len < cls.MAX_HEAD_LENGTH:
            # waiting for more data
            return None, 0
        # locate next header
        offset = data.find(sub=cls.MAGIC_CODE, start=(cls.MAGIC_CODE_OFFSET + 1))
        if offset == -1:
            # skip the whole buffer
            return None, -1
        assert offset > cls.MAGIC_CODE_OFFSET, 'magic code error: %s' % data
        # found next header, skip data before it
        offset -= cls.MAGIC_CODE_OFFSET
        data = data.slice(start=offset)
        # try again from new offset
        return Header.parse(data=data), offset

    @classmethod
    def parse(cls, data: ByteArray) -> (Optional[Package], int):
        # 1. seek header in received data
        head, offset = cls.seek_header(data=data)
        if offset < 0:
            # data error, ignore the whole buffer
            return None, -1
        if head is None:
            # header not found
            return None, offset
        # 2. check length
        data_len = data.size
        head_len = head.size
        body_len = head.body_length
        if body_len < 0:
            pack_len = data_len
        else:
            pack_len = head_len + body_len
        if data_len < pack_len:
            # package not completed, waiting for more data
            return None, offset
        elif data_len > pack_len:
            # cut the tail
            data = data.slice(start=0, end=pack_len)
        body = data.slice(start=head_len)
        return Package(data=data, head=head, body=body), offset

    @classmethod
    def create_command(cls, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.COMMAND,
                           body_length=body.size, body=body)

    @classmethod
    def create_message(cls, body: Union[bytes, ByteArray], sn: Optional[TransactionID] = None) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.MESSAGE, sn=sn, body_length=body.size, body=body)

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


class MTPStreamArrival(PackageArrival):
    """ MTP Stream Arrival Ship """

    @property
    def payload(self) -> bytes:
        pack = self.package
        if pack is not None:
            body = pack.body
            if body is not None:
                return body.get_bytes()


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

    def __append_cache(self, data: bytes):
        """ Append the data to the tail of memory cache """
        self.__chunks = self.__chunks.concat(data)

    def __join_cache(self, data: bytes) -> ByteArray:
        """ Join the memory cache and new data """
        chunks = self.__chunks.concat(data)
        self.__chunks = Data.ZERO
        return chunks

    def __push_back(self, data: ByteArray):
        """ Put the remaining data back to memory cache """
        self.__chunks = data.concat(self.__chunks)

    # Override
    def _parse_package(self, data: bytes) -> Optional[Package]:
        self.__processing += 1
        if self.__processing > 1:
            # it's already in processing now,
            # append the data to the tail of memory cache
            self.__append_cache(data=data)
            self.__processing -= 1
            return None
        # join the data to the memory cache
        buffer = self.__join_cache(data=data)
        # try to fetch a package
        pack, offset = PackUtils.parse(data=buffer)
        if offset < 0:
            # data error
            self.__processing -= 1
            return None
        # 'error part' + 'MTP package' + 'remaining data
        if pack is not None:
            offset += pack.size
        if offset == 0:
            self.__push_back(data=buffer)
        elif offset < buffer.size:
            buffer = buffer.slice(start=offset)
            self.__push_back(data=buffer)
        self.__processing -= 1
        return pack

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
    def check(cls, data: bytes) -> bool:
        head, offset = PackUtils.seek_header(data=Data(buffer=data))
        return head is not None


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
AGAIN = b'AGAIN'
