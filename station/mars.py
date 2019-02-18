# -*- coding: utf-8 -*-
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
    """
        Message Packer for Tencent/mars
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        data structure:
            head_length    - 4 bytes
            client_version - 4 bytes
            cmd_id         - 4 bytes
            seq            - 4 bytes
            body_len       - 4 bytes
            options        - variable length (head_length - 20)
    """

    def __new__(cls, data: bytes=None,
                client_version: int = 200, cmd_id: int=0, seq: int=0, options: bytes=None, body: bytes=None):
        """

        :param data:
        :param client_version:
        :param cmd_id:
        :param seq:
        :param options:
        :param body:
        :return:
        """
        if data:
            # return NetMsgHead object directly
            if isinstance(data, NetMsgHead):
                return data
            # check data length
            data_len = len(data)
            if data_len < MIN_HEAD_LEN:
                raise ValueError('net message pack data length error:', data_len)
            # get fields
            head_len = read_int(data, 0)
            client_version = read_int(data, 4)
            cmd_id = read_int(data, 8)
            seq = read_int(data, 12)
            body_len = read_int(data, 16)
            # check head length
            if MIN_HEAD_LEN <= head_len < data_len:
                data = data[:head_len]
            elif head_len > data_len:
                raise ValueError('net message pack head length error:', head_len)
            # get options
            if head_len == MIN_HEAD_LEN:
                options = None
            else:
                options = data[MIN_HEAD_LEN:]
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
            data = append_int(data, client_version)
            data = append_int(data, cmd_id)
            data = append_int(data, seq)
            data = append_int(data, body_len)
            if options:
                data = data + options
            if body:
                data = data
        # create net message head
        self = super().__new__(cls, data)
        self.head_length = head_len
        self.client_version = client_version
        self.cmd_id = cmd_id
        self.seq = seq
        self.body_length = body_len
        self.options = options
        return self


class NetMsg(bytes):

    def __new__(cls, data: bytes=None,
                head: bytes=None,
                client_version: int = 200, cmd_id: int = 0, seq: int = 0, options: bytes = None,
                body: bytes=None):
        """

        :param data:
        :param head:
        :param client_version:
        :param cmd_id:
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
            if pack_len < data_len:
                print('cut tail')
                data = data[:pack_len]
            # get body
            if head.body_length == 0:
                body = None
            elif pack_len <= len(data):
                body = data[head.head_length:]
            else:
                raise ValueError('body length error:', head.body_length)
        else:
            if head:
                head = NetMsgHead(head)
            else:
                head = NetMsgHead(client_version=client_version, cmd_id=cmd_id, seq=seq,
                                  options=options, body=body)
            if body:
                if head.body_length == len(body):
                    data = head + body
                else:
                    raise ValueError('body length error:', head.body_length)
            elif head.body_length == 0:
                data = head
            else:
                raise ValueError('body length error:', head.body_length)
        # create net message package
        self = super().__new__(cls, data)
        self.head = head
        self.body = body
        return self
