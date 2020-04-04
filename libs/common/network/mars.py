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


def read_int(data, pos):
    return int.from_bytes(bytes=data[pos:pos + 4], byteorder='big')


def append_int(data, i: int):
    return data + i.to_bytes(length=4, byteorder='big')


MIN_HEAD_LEN = 4 + 4 + 4 + 4 + 4


class NetMsgHead(bytes):

    SEND_MSG = 3
    NOOP = 6

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

    def __new__(cls, data: bytes=None,
                version: int = 200, cmd: int=0, seq: int=0, options: bytes=None, body: bytes=None):
        """

        :param data:    msg pack head data (if data is None, use other parameters to create msg head)
        :param version: client version
        :param cmd:     cmd id
        :param seq:     serial number
        :param options: extra parameters
        :param body:    msg body
        :return:
        """
        if data:
            # return NetMsgHead object directly
            if isinstance(data, NetMsgHead):
                return data
            # check data length
            data_len = len(data)
            if data_len < MIN_HEAD_LEN:
                raise ValueError('net message pack data length error: %d' % data_len)
            # get fields
            head_len = read_int(data, 0)
            version = read_int(data, 4)
            cmd = read_int(data, 8)
            seq = read_int(data, 12)
            body_len = read_int(data, 16)
            # check head length
            if data_len < head_len or head_len < MIN_HEAD_LEN:
                raise ValueError('net message pack head length error: %d' % head_len)
            elif data_len > head_len:
                # cut head
                data = data[:head_len]
            # get options
            if head_len == MIN_HEAD_LEN:
                options = None
            else:
                options = data[MIN_HEAD_LEN:]
            # check body length
            if body_len < 0:
                raise ValueError('net message pack body length error: %d' % body_len)
        else:
            if options:
                head_len = MIN_HEAD_LEN + len(options)
            else:
                head_len = MIN_HEAD_LEN
            if body:
                body_len = len(body)
            else:
                body_len = 0
            data = b''
            data = append_int(data, head_len)
            data = append_int(data, version)
            data = append_int(data, cmd)
            data = append_int(data, seq)
            data = append_int(data, body_len)
            if options:
                data = data + options
        # create net message head
        self = super().__new__(cls, data)
        self.head_length = head_len
        self.version = version
        self.cmd = cmd
        self.seq = seq
        self.body_length = body_len
        self.options = options
        return self


class NetMsg(bytes):

    def __new__(cls, data: bytes=None,
                head: bytes=None,
                version: int=200, cmd: int=0, seq: int=0, options: bytes=None, body: bytes=None):
        """

        :param data:    msg pack data (if data is None, use other parameters to create msg pack)
        :param head:    msg pack head data (if head is None, use other parameters to create msg head)
        :param version:
        :param cmd:
        :param seq:
        :param options:
        :param body:
        :return:
        """
        if data:
            # return NetMsg object directly
            if isinstance(data, NetMsg):
                return data
            # check head
            if head is None:
                head = NetMsgHead(data)
            # check pack length
            pack_len = head.head_length + head.body_length
            data_len = len(data)
            if data_len < pack_len:
                raise ValueError('data length error: %d < %d' % (data_len, pack_len))
            elif data_len > pack_len:
                # cut package
                data = data[:pack_len]
            # get body
            if head.body_length == 0:
                body = None
            else:
                body = data[head.head_length:]
        elif head:
            head = NetMsgHead(head)
            if body:
                if head.body_length == len(body):
                    data = head + data
                else:
                    raise ValueError('body length error:', head.body_length)
            else:
                data = head
        else:
            # if head is None, use other parameters to create head
            head = NetMsgHead(version=version, cmd=cmd, seq=seq, options=options, body=body)
            if body:
                data = head + body
            else:
                data = head
        # create net message package
        self = super().__new__(cls, data)
        self.head = head
        self.body = body
        return self
