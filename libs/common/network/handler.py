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

from dmtp.mtp import Header, Package

from ...utils import Logging
from ...utils.mtp import MTPUtils

from .ws import WebSocket
from .mars import NetMsgHead, NetMsg


class ConnectionDelegate:

    @abstractmethod
    def connection_received(self, connection, data: bytes) -> bytes:
        """
        Callback for received data package

        :param connection:
        :param data: data package
        :return response
        """
        raise NotImplemented

    @abstractmethod
    def connection_reconnected(self, connection):
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
                connection.send(data=pack)
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
            connection.send(data=data)
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
                data = self.connection_pack(connection=connection, data=res)
                connection.send(data=data)
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
            return mars, stream[mars.length:]
        except ValueError:
            # mars package head error
            pos = stream.find(b'\x00\x00\x00\xc8\x00\x00\x00', start=1)
            if pos > 0:
                self.error('sticky mars packages, cut the head: %s' % (stream[:pos]))
                return b'', stream[pos:]
            else:
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
        if isinstance(mars, NetMsg):
            # process data package and get response
            head = mars.head
            # check cmd
            if head.cmd == head.SEND_MSG:
                # TODO: handle SEND_MSG request
                if head.body_length == 0:
                    raise ValueError('mars body not found: %s' % stream)
                delegate = self.connection_delegate(connection=connection)
                res = delegate.connection_received(connection=connection, data=mars.body)
                if res is not None:
                    head = NetMsgHead.new(cmd=head.cmd, seq=head.seq, body_len=len(res))
                    msg = NetMsg.new(head=head, body=res)
                    connection.send(data=msg.body)
            elif head.cmd == head.NOOP:
                # TODO: handle NOOP request
                self.debug('mars NOOP, cmd=%d, seq=%d: %s' % (head.cmd, head.seq, stream))
            else:
                # TODO: handle Unknown request
                self.warning('mars unknown, cmd=%d, seq=%d: %s' % (head.cmd, head.seq, stream))
                head = NetMsgHead.new(cmd=6, seq=0)
                msg = NetMsg.new(head=head)
                connection.send(data=msg.body)
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        head = NetMsgHead.new(cmd=10001, seq=0, body_len=len(data))
        msg = NetMsg.new(head=head, body=data)
        return msg.data


#
#   D-MTP
#
class DMTPHandler(ConnectionHandler, Logging):

    @classmethod
    def parse_head(cls, stream: bytes) -> Optional[Header]:
        return MTPUtils.parse_head(data=stream)

    def parse_package(self, stream: bytes) -> (Package, bytes):
        mtp = MTPUtils.parse_package(data=stream)
        if mtp is None:
            pos = stream.find(b'DIM', start=1)
            if pos > 0:
                self.error('sticky D-MTP packages, cut the head: %s' % (stream[:pos]))
                return b'', stream[pos:]
            else:
                # incomplete package?
                return None, stream
        else:
            return mtp, stream[mtp.length:]

    def connection_process(self, connection, stream: bytes = b'') -> bool:
        stream = self._remaining + stream
        # try to get D-MTP package
        mtp, stream = self.parse_package(stream=stream)
        self._remaining = stream
        if mtp is None:
            # partially package? keep it for next received
            return False
        if isinstance(mtp, Package):
            # process data package and get response
            head = mtp.head
            body = mtp.body
            body_len = body.length
            if body_len == 0:
                res = b'NOOP'
            elif body_len == 4 and body == b'PING':
                res = b'PONG'
            else:
                delegate = self.connection_delegate(connection=connection)
                res = delegate.connection_received(connection=connection, data=body.get_bytes())
            pack = MTPUtils.create_package(body=res, data_type=head.data_type, sn=head.sn)
            connection.send(data=pack.get_bytes())
        # check remaining
        return len(self._remaining) > 0

    def connection_pack(self, connection, data: bytes) -> bytes:
        pack = MTPUtils.create_package(body=data)
        return pack.get_bytes()
