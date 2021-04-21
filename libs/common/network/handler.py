# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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

"""
    Socket Connection
    ~~~~~~~~~~~~~~~~~

    Connection for DIM Station and Robot Client
"""

from abc import abstractmethod
from typing import Optional

from dmtp.mtp import Header as MTPHeader, Package as MTPPackage
from dmtp.mtp import Command as MTPCommand, CommandRespond as MTPCommandRespond
from dmtp.mtp import Message as MTPMessage, MessageRespond as MTPMessageRespond
from dmtp.mtp import MessageFragment as MTPMessageFragment

from ...utils import Logging
from ...utils.mtp import MTPUtils

from .ws import WebSocket
from .mars import NetMsgHead, NetMsg


class ConnectionDelegate:

    @abstractmethod
    def connection_received(self, connection, data: bytes) -> Optional[bytes]:
        """
        Callback for received data package

        :param connection:
        :param data: data package
        :return response
        """
        raise NotImplemented

    @abstractmethod
    def connection_connected(self, connection):
        pass


class ConnectionHandler:

    def __init__(self):
        super().__init__()
        self._remaining = b''

    @classmethod
    def connection_delegate(cls, connection) -> ConnectionDelegate:
        return connection.delegate

    @abstractmethod
    def connection_process(self, connection, stream: bytes = b'') -> bool:
        """
        Process received data stream

        :param connection:
        :param stream: received data
        :return True on process again
        """
        raise NotImplemented

    @abstractmethod
    def connection_pack(self, connection, data: bytes) -> bytes:
        """
        Pack data for sending out

        :param connection:
        :param data:
        :return: packed data
        """
        raise NotImplemented


#
#   Raw JsON
#
class JSONHandler(ConnectionHandler):

    @classmethod
    def parse_package(cls, stream: bytes) -> (bytes, bytes):
        pos = stream.find(b'\n')
        if pos < 0:
            return None, stream
        else:
            return stream[:pos], stream[pos+1:]

    def connection_process(self, connection, stream: bytes = b'') -> bool:
        stream = self._remaining + stream
        # try to parse JSON package
        data, stream = self.parse_package(stream=stream)
        self._remaining = stream
        if data is None:
            # partially package? keep it for next received
            return False
        if len(data) > 0:
            # process data package and get response
            delegate = self.connection_delegate(connection=connection)
            res = delegate.connection_received(connection=connection, data=data)
            if res is not None and len(res) > 0:
                pack = self.connection_pack(connection=connection, data=res)
                connection.sendall(data=pack)
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        return data + b'\n'


#
#   Web Socket
#
class WebSocketHandler(ConnectionHandler):

    def __init__(self):
        super().__init__()
        self.__ws = WebSocket()

    @classmethod
    def is_handshake(cls, stream: bytes):
        return WebSocket.is_handshake(stream=stream)

    def parse_package(self, stream: bytes) -> (bytes, bytes):
        return self.__ws.parse(stream=stream)

    def connection_process(self, connection, stream: bytes = b'') -> bool:
        stream = self._remaining + stream
        if self.is_handshake(stream=stream):
            # respond handshake package
            data = self.__ws.handshake(stream=stream)
            connection.sendall(data=data)
            # FIXME: what about sticky packages?
            self._remaining = b''
            return False
        # normal package
        data, stream = self.parse_package(stream=stream)
        self._remaining = stream
        if data is None:
            # partially package? keep it for next received
            return False
        if len(data) > 0:
            # process data package and get response
            delegate = self.connection_delegate(connection=connection)
            res = delegate.connection_received(connection=connection, data=data)
            if res is not None and len(res) > 0:
                pack = self.connection_pack(connection=connection, data=res)
                connection.sendall(data=pack)
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        return self.__ws.pack(payload=data)


#
#   Tencent mars
#
class MarsHandler(ConnectionHandler, Logging):

    @classmethod
    def parse_head(cls, stream: bytes) -> Optional[NetMsgHead]:
        try:
            head = NetMsgHead.parse(data=stream)
            if head.version != 200:
                return None
            if head.cmd not in [head.SEND_MSG, head.NOOP]:
                return None
            # OK
            return head
        except ValueError:
            return None

    def parse_package(self, stream: bytes) -> (NetMsg, bytes):
        try:
            mars = NetMsg.parse(data=stream)
            head = mars.head
            if head.length + head.body_length <= len(stream):
                return mars, stream[mars.length:]
        except ValueError:
            # mars package head error
            pos = stream.find(b'\x00\x00\x00\xc8\x00\x00\x00', 1)
            if pos > 0:
                self.error('sticky mars packages, cut the head: %s' % (stream[:pos]))
                return b'', stream[pos:]
        # incomplete package?
        return None, stream

    def connection_process(self, connection, stream: bytes = b'') -> bool:
        stream = self._remaining + stream
        # try to get mars package
        mars, stream = self.parse_package(stream=stream)
        self._remaining = stream
        if mars is None:
            # partially package? keep it for next received
            return False
        if not isinstance(mars, NetMsg):
            # sticky mars packages
            return False
        # process data package and get response
        head = mars.head
        # check cmd
        if head.cmd == head.SEND_MSG:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('mars body not found: %s' % stream)
            delegate = self.connection_delegate(connection=connection)
            res = delegate.connection_received(connection=connection, data=mars.body)
            if res is None:
                res = b''
            head = NetMsgHead.new(cmd=head.cmd, seq=head.seq, body_len=len(res))
            msg = NetMsg.new(head=head, body=res)
        elif head.cmd == head.NOOP:
            # TODO: handle NOOP request
            self.debug('mars NOOP, cmd=%d, seq=%d: %s' % (head.cmd, head.seq, stream))
            msg = mars
        else:
            # TODO: handle Unknown request
            self.warning('mars unknown, cmd=%d, seq=%d: %s' % (head.cmd, head.seq, stream))
            head = NetMsgHead.new(cmd=NetMsgHead.NOOP, seq=0)
            msg = NetMsg.new(head=head)
        connection.sendall(data=msg.data)
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, seq=0, body_len=len(data))
        msg = NetMsg.new(head=head, body=data)
        return msg.data


#
#   MTP
#
class MTPHandler(ConnectionHandler, Logging):

    @classmethod
    def parse_head(cls, stream: bytes) -> Optional[MTPHeader]:
        return MTPUtils.parse_head(data=stream)

    def parse_package(self, stream: bytes) -> (MTPPackage, bytes):
        # 1. check received data
        data_len = len(stream)
        try:
            head = MTPUtils.parse_head(data=stream)
        except Exception as error:
            self.error('failed to parse MTP head: %s' % error)
            head = None
        if head is None:
            # not a MTP package?
            if data_len < 20:
                # wait for more data
                return None, stream
            pos = stream.find(b'DIM', 1)
            if pos > 0:
                # found next head(starts with 'DIM'), skip data before it
                self.error('sticky MTP packages, cut the head: %s' % (stream[:pos]))
                return b'', stream[pos:]
            else:
                # skip the whole data
                self.error('MTP head error, drop it: %s' % stream)
                return b'', b''
        # 2. receive data with 'head.length + body.length'
        head_len = head.length
        body_len = head.body_length
        if body_len < 0:
            # should not happen
            body_len = data_len - head_len
        pack_len = head_len + body_len
        if data_len < pack_len:
            # wait for more data
            return None, stream
        # check for remaining data
        if data_len == pack_len:
            remaining = b''
        else:
            remaining = stream[pack_len:]
            stream = stream[:pack_len]
        # return package & remaining data
        mtp = MTPUtils.parse_package(data=stream)
        return mtp, remaining

    def connection_process(self, connection, stream: bytes = b'') -> bool:
        stream = self._remaining + stream
        # try to get MTP package
        mtp, stream = self.parse_package(stream=stream)
        self._remaining = stream
        if mtp is None:
            # partially package? keep it for next received
            return False
        if isinstance(mtp, MTPPackage):
            # process data package and get response
            head = mtp.head
            body = mtp.body
            # check data type
            if head.data_type == MTPCommand:
                # respond for Command
                if body == b'PING':
                    res = MTPUtils.create_package(body=b'PONG', data_type=MTPMessageRespond, sn=head.sn)
                    connection.sendall(data=res.get_bytes())
                return True
            elif head.data_type == MTPCommandRespond:
                # process Command Respond
                return True
            elif head.data_type == MTPMessageFragment:
                # respond for Message Fragment
                return True
            elif head.data_type == MTPMessage:
                # respond for Message
                res = MTPUtils.create_package(body=b'OK', data_type=MTPMessageRespond, sn=head.sn)
                connection.sendall(data=res.get_bytes())
            else:
                assert head.data_type == MTPMessageRespond, 'data type error: %s' % head.data_type
                # process Message Respond
                if body == b'OK':
                    # just ignore
                    return True
                elif body == b'AGAIN':
                    # TODO: mission failed, send the message again
                    return True
            # process received package
            delegate = self.connection_delegate(connection=connection)
            res = delegate.connection_received(connection=connection, data=body.get_bytes())
            if res is not None and len(res) > 0:
                pack = MTPUtils.create_package(body=res, data_type=MTPMessage)
                connection.sendall(data=pack.get_bytes())
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        pack = MTPUtils.create_package(body=data, data_type=MTPMessage)
        return pack.get_bytes()
