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
from typing import TypeVar, Generic, Optional

from udp.ba import ByteArray
from udp.mtp import Header, Package

from .protocol import NetMsgHead, NetMsg


H = TypeVar('H')
P = TypeVar('P')


class PackageSeeker(Generic[H, P]):

    def __init__(self, magic_code: bytes, magic_offset: int, max_head_length: int):
        super().__init__()
        self.__magic_code = magic_code
        self.__magic_offset = magic_offset
        self.__max_head_length = max_head_length

    @abstractmethod
    def parse_header(self, data: ByteArray) -> Optional[H]:
        """ Get package header from data buffer """
        raise NotImplemented

    @abstractmethod
    def get_head_length(self, head: H) -> int:
        """ Get length of header """
        raise NotImplemented

    @abstractmethod
    def get_body_length(self, head: H) -> int:
        """ Get body length from header """
        raise NotImplemented

    @abstractmethod
    def create_package(self, data: ByteArray, head: H, body: ByteArray) -> P:
        """ Create package with buffer, head & body """
        raise NotImplemented

    def seek_header(self, data: ByteArray) -> (Optional[H], int):
        """
        Seek package header in received data buffer

        :param data: received data buffer
        :return: header and it's offset, -1 on data error
        """
        head = self.parse_header(data=data)
        if head is not None:
            # got it (offset = 0)
            return head, 0
        data_len = data.size
        if data_len < self.__max_head_length:
            # waiting for more data
            return None, 0
        # locate next header
        offset = data.find(sub=self.__magic_code, start=(self.__magic_offset + 1))
        if offset < 0:
            if data_len < 65536:
                # waiting for more data
                return None, 0
            # skip the whole buffer
            return None, -1
        assert offset > self.__magic_offset, 'magic code error: %s' % data
        # found next header, skip data before it
        offset -= self.__magic_offset
        data = data.slice(start=offset)
        # try again from new offset
        head = self.parse_header(data=data)
        return head, offset

    def seek_package(self, data: ByteArray) -> (Optional[P], int):
        """
        Seek data package from received data buffer

        :param data: received data buffer
        :return: package and it's offset, -1 on data error
        """
        # 1. seek header in received data
        head, offset = self.seek_header(data=data)
        if offset < 0:
            # data error, ignore the whole buffer
            return None, -1
        elif head is None:
            # header not found
            return None, offset
        elif offset > 0:
            # drop the error part
            data = data.slice(start=offset)
        # 2. check length
        data_len = data.size
        head_len = self.get_head_length(head=head)
        body_len = self.get_body_length(head=head)
        if body_len < 0:
            pack_len = data_len
        else:
            pack_len = head_len + body_len
        # check data buffer
        if data_len < pack_len:
            # package not completed, waiting for more data
            return None, offset
        elif data_len > pack_len:
            # cut the tail
            data = data.slice(start=0, end=pack_len)
        # OK
        body = data.slice(start=head_len)
        pack = self.create_package(data=data, head=head, body=body)
        return pack, offset


class MTPPackageSeeker(PackageSeeker[Header, Package]):
    """ MTP Package Seeker """

    def __init__(self):
        super().__init__(magic_code=Header.MAGIC_CODE, magic_offset=0, max_head_length=24)

    # Override
    def parse_header(self, data: ByteArray) -> Optional[Header]:
        return Header.parse(data=data)

    # Override
    def get_head_length(self, head: Header) -> int:
        return head.size

    # Override
    def get_body_length(self, head: Header) -> int:
        return head.body_length

    # Override
    def create_package(self, data: ByteArray, head: Header, body: ByteArray) -> Package:
        return Package(data=data, head=head, body=body)


class MarsPackageSeeker(PackageSeeker[NetMsgHead, NetMsg]):
    """ Mars Package Seeker """

    def __init__(self):
        code = NetMsgHead.MAGIC_CODE
        offset = NetMsgHead.MAGIC_CODE_OFFSET
        length = NetMsgHead.MIN_HEAD_LEN + 12  # FIXME: len(options) > 12?
        super().__init__(magic_code=code, magic_offset=offset, max_head_length=length)

    def parse_header(self, data: ByteArray) -> Optional[NetMsgHead]:
        data = data.get_bytes()
        return parse_mars_head(data=data)

    def get_head_length(self, head: NetMsgHead) -> int:
        return head.length

    def get_body_length(self, head: NetMsgHead) -> int:
        return head.body_length

    def create_package(self, data: ByteArray, head: NetMsgHead, body: ByteArray) -> NetMsg:
        data = data.get_bytes()
        if body.size == 0:
            body = None
        else:
            body = body.get_bytes()
        return NetMsg(data=data, head=head, body=body)


def parse_mars_head(data: bytes) -> Optional[NetMsgHead]:
    head = NetMsgHead.parse(data=data)
    if head is not None:
        if head.version != 200:
            return None
        if head.cmd not in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP, NetMsgHead.PUSH_MESSAGE]:
            return None
        if head.body_length < 0:
            return None
        return head
