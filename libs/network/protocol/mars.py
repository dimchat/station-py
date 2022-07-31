# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Tencent Mars Protocol
    ~~~~~~~~~~~~~~~~~~~~~
"""

import random
import threading
from typing import Optional


def read_int(data, pos):
    return int.from_bytes(bytes=data[pos:pos + 4], byteorder='big')


def append_int(data, i: int):
    return data + i.to_bytes(length=4, byteorder='big')


class NetMsgHead:

    MIN_HEAD_LEN = 4 + 4 + 4 + 4 + 4

    MAGIC_CODE = b'\x00\x00\x00\xc8\x00\x00\x00'  # version = 0xC8
    MAGIC_CODE_OFFSET = 4

    # cmd
    SAY_HELLO = 1
    CONV_LST = 2
    SEND_MSG = 3
    NOOP = 6
    PUSH_MESSAGE = 10001

    """
        Message Packer for Tencent/mars
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        data structure:
            head_length - 4 bytes
            version     - 4 bytes
            cmd         - 4 bytes
            seq         - 4 bytes
            body_len    - 4 bytes
            options     - variable length (head_length - 20)
    """

    def __init__(self, data: bytes,
                 version: int = 200, cmd: int = 0, seq: int = 0, options: bytes = None, body_len: int = 0):
        """

        :param data:    msg pack head data (if data is None, use other parameters to create msg head)
        :param version: client version
        :param cmd:     cmd id
        :param seq:     serial number
        :param options: extra parameters
        :param body_len:msg body length
        :return:
        """
        # create net message head
        super().__init__()
        self.__data = data
        self.__version = version
        self.__cmd = cmd
        self.__seq = seq
        self.__options = options
        self.__body_length = body_len

    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s: %d| cmd=%d, seq=%d, body_len=%d />' % (cname, self.version, self.cmd, self.seq, self.body_length)

    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s: %d| cmd=%d, seq=%d, body_len=%d />' % (cname, self.version, self.cmd, self.seq, self.body_length)

    @property
    def data(self) -> bytes:
        return self.__data

    @property
    def length(self) -> int:
        return len(self.__data)

    @property
    def version(self) -> int:
        return self.__version

    @property
    def cmd(self) -> int:
        return self.__cmd

    @property
    def seq(self) -> int:
        return self.__seq

    @property
    def options(self) -> Optional[bytes]:
        return self.__options

    @property
    def body_length(self) -> int:
        return self.__body_length

    @classmethod
    def new(cls, version: int = 200, cmd: int = 0, seq: int = 0, options: bytes = None, body_len: int = 0):
        if options:
            head_len = cls.MIN_HEAD_LEN + len(options)
        else:
            head_len = cls.MIN_HEAD_LEN
        # prepare data
        data = b''
        data = append_int(data, head_len)
        data = append_int(data, version)
        data = append_int(data, cmd)
        data = append_int(data, seq)
        data = append_int(data, body_len)
        if options:
            data = data + options
        return cls(data=data, version=version, cmd=cmd, seq=seq, options=options, body_len=body_len)

    @classmethod
    def parse(cls, data: bytes):
        # check data length
        data_len = len(data)
        if data_len < cls.MIN_HEAD_LEN:
            # raise ValueError('Mars data length error: %d' % data_len)
            return None
        # get fields
        head_len = read_int(data, 0)
        version = read_int(data, 4)
        cmd = read_int(data, 8)
        seq = read_int(data, 12)
        body_len = read_int(data, 16)
        assert head_len >= cls.MIN_HEAD_LEN, 'Mars head length error: %d' % head_len
        assert version == 200, 'Mars version error: %d' % version
        assert cmd in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP, NetMsgHead.PUSH_MESSAGE], 'Mars cmd error: %d' % cmd
        assert body_len >= 0, 'Mars body length error: %d' % body_len
        # check head length
        if data_len < head_len:
            # raise ValueError('Mars head length error: %d' % head_len)
            return None
        elif data_len > head_len:
            # cut head
            data = data[:head_len]
        # get options
        if head_len == cls.MIN_HEAD_LEN:
            options = None
        else:
            options = data[cls.MIN_HEAD_LEN:]
        # check body length
        if body_len < 0:
            # raise ValueError('Mars body length error: %d' % body_len)
            return None
        return cls(data=data, version=version, cmd=cmd, seq=seq, options=options, body_len=body_len)


class NetMsg:

    def __init__(self, data: bytes, head: NetMsgHead, body: bytes = None):
        """

        :param data: msg pack data (if data is None, use other parameters to create msg pack)
        :param head: msg pack head data (if head is None, use other parameters to create msg head)
        :param body: msg pack body
        :return:
        """
        super(NetMsg, self).__init__()
        self.__data = data
        self.__head = head
        self.__body = body

    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s body_len=%d>%s</%s module="%s">' % (cname, self.body_length, self.head, cname, mod)

    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s body_len=%d>%s</%s module="%s">' % (cname, self.body_length, self.head, cname, mod)

    @property
    def data(self) -> bytes:
        return self.__data

    @property
    def length(self) -> int:
        return len(self.__data)

    @property
    def head(self) -> NetMsgHead:
        return self.__head

    @property
    def body(self) -> Optional[bytes]:
        return self.__body

    @property
    def body_length(self) -> int:
        body = self.body
        if body is None:
            return 0
        else:
            return len(body)

    @classmethod
    def new(cls, head: NetMsgHead, body: bytes = None):
        if body is None:
            data = head.data
        else:
            data = head.data + body
        return cls(data=data, head=head, body=body)

    @classmethod
    def parse(cls, data: bytes):
        head = NetMsgHead.parse(data=data)
        if head is None:
            # raise AssertionError('Mars head error')
            return None
        head_len = head.length
        body_len = head.body_length
        pack_len = head_len + body_len
        if len(data) > pack_len:
            data = data[:pack_len]
        if body_len > 0:
            start = head_len
            end = start + body_len
            body = data[start:end]
        else:
            body = None
        return cls(data=data, head=head, body=body)


#
#   msg.head.seq
#


def random_int(size: int) -> int:
    # return bytes(numpy.random.bytes(size))
    return random.getrandbits(size * 8)


class NetMsgSeq:

    __number_lock = threading.Lock()
    __number = random_int(size=4)

    @classmethod
    def generate(cls) -> int:
        with cls.__number_lock:
            if cls.__number < 0xFFFFFFFF:
                cls.__number += 1
            else:
                cls.__number = 0
            return cls.__number
