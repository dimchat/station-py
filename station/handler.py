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

"""
    Request Handler
    ~~~~~~~~~~~~~~~

    Handler for each connection
"""

import traceback
from socketserver import StreamRequestHandler
from typing import Optional

from dimp import json_encode
from dimp import User
from dimp import InstantMessage, ReliableMessage
from dimsdk import CompletionHandler
from dimsdk import MessengerDelegate

from libs.utils import Log
from libs.utils import NotificationCenter
from libs.common import NotificationNames
from libs.common import NetMsgHead, NetMsg
from libs.common import WebSocket
from libs.common import CommonPacker
from libs.server import ServerMessenger, SessionServer, Session

from libs.utils.mtp import MTPUtils

from robots.nlp import chat_bots

from station.config import current_station


class RequestHandler(StreamRequestHandler, MessengerDelegate, Session.Handler):

    def __init__(self, request, client_address, server):
        # messenger
        self.__messenger: Optional[ServerMessenger] = None
        self.__session: Optional[Session] = None
        # handlers with Protocol
        self.__process_package = None
        self.__push_data = None
        # init
        super().__init__(request=request, client_address=client_address, server=server)

    # def __del__(self):
    #     Log.info('request handler deleted: %s' % str(self.client_address))

    def debug(self, msg: str):
        Log.debug('%s >\t%s' % (self.__class__.__name__, msg))

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def warning(self, msg: str):
        Log.warning('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def messenger(self) -> ServerMessenger:
        if self.__messenger is None:
            m = ServerMessenger()
            m.delegate = self
            # set context
            m.context['station'] = current_station
            m.context['bots'] = chat_bots(names=['tuling', 'xiaoi'])  # chat bots
            m.context['remote_address'] = self.client_address
            self.__messenger = m
        return self.__messenger

    @property
    def session_server(self) -> SessionServer:
        return self.messenger.session_server

    @property
    def remote_user(self) -> Optional[User]:
        if self.__messenger is not None:
            return self.__messenger.remote_user

    #
    #
    #
    def setup(self):
        super().setup()
        timeout = self.request.gettimeout()
        if timeout is None:
            self.timeout = 300
        else:
            self.timeout = timeout
        self.__session = self.session_server.get_session(client_address=self.client_address, handler=self)
        NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
            'session': self.__session,
        })
        self.info('client connected: %s' % self.__session)

    def finish(self):
        self.info('client disconnected: %s' % self.__session)
        NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
            'session': self.__session,
        })
        self.session_server.remove_session(session=self.__session)
        self.__session = None
        self.__messenger = None
        super().finish()

    """
        DIM Request Handler
    """

    def handle(self):
        data = b''
        while True:
            # receive all data
            remaining_length = len(data)
            data = self.receive(data)
            if len(data) == remaining_length:
                self.info('no more data, exit %s, remaining=%d' % (self.client_address, remaining_length))
                break

            # check protocol
            while self.__process_package is None:

                # (Protocol A) D-MTP?
                if MTPUtils.parse_head(data=data) is not None:
                    # it seems be a D-MTP package!
                    self.__process_package = self.process_dmtp_package
                    self.__push_data = self.push_dmtp_data
                    packer = self.messenger.packer
                    assert isinstance(packer, CommonPacker), 'packer error: %s' % packer
                    packer.mtp_format = packer.MTP_DMTP
                    break

                # (Protocol B) Web socket?
                if WebSocket.is_handshake(stream=data):
                    # it seems be a Web socket package!
                    self.__process_package = self.process_ws_handshake
                    self.__push_data = self.push_ws_data
                    break

                # (Protocol C) Tencent mars?
                if self.parse_mars_head(data=data) is not None:
                    # it seems be a mars package!
                    self.__process_package = self.process_mars_package
                    self.__push_data = self.push_mars_data
                    break

                # (Protocol D) raw data (JSON in line)?
                if data.startswith(b'{"') and data.find(b'\0') < 0:
                    # treat it as raw data in JSON format
                    self.__process_package = self.process_raw_package
                    self.__push_data = self.push_raw_data
                    break

                # unknown protocol
                data = b''
                # raise AssertionError('unknown protocol')
                break
            if self.__process_package is None:
                continue

            # process package(s) one by one
            #    the received data packages maybe sticky
            n_len = len(data)
            o_len = n_len + 1
            while n_len < o_len:
                o_len = n_len
                data = self.__process_package(data)
                n_len = len(data)

    #
    #   Protocol: D-MTP
    #
    def process_dmtp_package(self, data: bytes) -> bytes:
        # 1. check received data
        data_len = len(data)
        head = MTPUtils.parse_head(data=data)
        if head is None:
            # not a D-MTP package?
            if data_len < 20:
                # wait for more data
                return data
            pos = data.find(b'DIM', start=1)
            if pos > 0:
                # found next head(starts with 'DIM'), skip data before it
                return data[pos:]
            else:
                # skip the whole data
                return b''
        # 2. receive data with 'head.length + body.length'
        head_len = head.length
        body_len = head.body_length
        if body_len < 0:
            # should not happen
            body_len = data_len - head_len
        pack_len = head_len + body_len
        if pack_len > data_len:
            # wait for more data
            return data
        # check remaining data
        if pack_len < data_len:
            remaining = data[pack_len:]
            data = data[:pack_len]
        else:
            remaining = b''
        # 3. package body
        body = data[head_len:]
        if body_len == 0:
            res = b'NOOP'
        elif body_len == 4 and body == b'PING':
            res = b'PONG'
        else:
            res = self.received_package(pack=body)
        pack = MTPUtils.create_package(body=res, data_type=head.data_type, sn=head.sn)
        self.send(data=pack.get_bytes())
        return remaining

    def push_dmtp_data(self, body: bytes) -> bool:
        pack = MTPUtils.create_package(body=body)
        return self.send(data=pack.get_bytes())

    #
    #   Protocol: WebSocket
    #
    def process_ws_handshake(self, pack: bytes):
        ws = WebSocket()
        res = ws.handshake(stream=pack)
        self.send(res)
        self.__process_package = self.process_ws_package
        return b''

    def process_ws_package(self, pack: bytes) -> bytes:
        ws = WebSocket()
        data, remaining = ws.parse(stream=pack)
        if data is not None:
            res = self.received_package(pack=data)
            self.push_ws_data(res)
        return remaining

    def push_ws_data(self, body: bytes) -> bool:
        ws = WebSocket()
        pack = ws.pack(payload=body)
        return self.send(data=pack)

    #
    #   Protocol: Tencent mars
    #
    @staticmethod
    def parse_mars_head(data: bytes) -> Optional[NetMsgHead]:
        try:
            head = NetMsgHead.parse(data=data)
            if head.version != 200:
                return None
            if head.cmd not in [head.SEND_MSG, head.NOOP]:
                return None
            # OK
            return head
        except ValueError:
            return None

    def process_mars_package(self, pack: bytes) -> bytes:
        # check package head
        if self.parse_mars_head(data=pack) is None:
            if len(pack) < 20:
                return pack
            pos = pack.find(b'\x00\x00\x00\xc8\x00\x00\x00', start=4)
            if pos > 4:
                self.error('sticky mars, cut the head: %s' % (pack[:pos-4]))
                return pack[pos-4:]
            self.error('not a mars pack, drop it: %s' % pack)
            head = NetMsgHead.new(cmd=6, seq=0)
            msg = NetMsg.new(head=head)
            self.send(data=msg.data)
            return b''
        # try to get complete package
        try:
            mars = NetMsg.parse(data=pack)
        except ValueError:
            # partially package? keep it for next loop
            return pack
        head = mars.head
        pack_len = head.length + head.body_length
        # cut sticky packages
        remaining = pack[pack_len:]
        pack = pack[:pack_len]
        # check cmd
        if head.cmd == head.SEND_MSG:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('mars body not found: %s, remaining: %d' % (pack, len(remaining)))
            body = self.received_package(mars.body)
            head = NetMsgHead.new(cmd=head.cmd, seq=head.seq, body_len=len(body))
            msg = NetMsg.new(head=head, body=body)
            res = msg.data
        elif head.cmd == head.NOOP:
            # TODO: handle NOOP request
            self.debug('mars NOOP, cmd=%d, seq=%d: %s, remaining: %d' % (head.cmd, head.seq, pack, len(remaining)))
            res = pack
        else:
            # TODO: handle Unknown request
            self.warning('mars unknown, cmd=%d, seq=%d: %s, remaining: %d' % (head.cmd, head.seq, pack, len(remaining)))
            head = NetMsgHead.new(cmd=6, seq=0)
            msg = NetMsg.new(head=head)
            res = msg.data
        self.send(res)
        # return the remaining incomplete package
        return remaining

    def push_mars_data(self, body: bytes) -> bool:
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        head = NetMsgHead.new(cmd=10001, seq=0, body_len=len(body))
        msg = NetMsg.new(head=head, body=body)
        return self.send(data=msg.data)

    #
    #   Protocol: raw data (JSON string)
    #
    def process_raw_package(self, pack: bytes) -> bytes:
        # skip leading empty packages
        pack = pack.lstrip()
        if len(pack) == 0:
            # NOOP: heartbeat package
            self.debug('respond <heartbeats>: %s' % self.__session)
            self.send(b'\n')
            return b''
        # check whether contain incomplete message
        pos = pack.rfind(b'\n')
        if pos < 0:
            # partially package? keep it for next loop
            return pack
        # maybe more than one message in a time
        res = self.received_package(pack[:pos])
        self.send(res + b'\n')
        # return the remaining incomplete package
        return pack[pos+1:]

    def push_raw_data(self, body: bytes) -> bool:
        data = body + b'\n'
        return self.send(data=data)

    def push_message(self, msg: ReliableMessage) -> bool:
        body = json_encode(msg.dictionary)
        return self.__push_data(body=body)

    #
    #   receive message(s)
    #
    def received_package(self, pack: bytes) -> Optional[bytes]:
        if pack.startswith(b'{'):
            # JsON in lines
            packages = pack.splitlines()
        else:
            packages = [pack]
        data = b''
        for pack in packages:
            try:
                res = self.messenger.process_package(data=pack)
                if res is not None:
                    data = res + b'\n'
            except Exception as error:
                self.error('parse message failed: %s' % error)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        # station MUST respond something to client request
        if len(data) > 0:
            data = data[:-1]  # remove last '\n'
        return data

    #
    #   Socket IO
    #
    @property
    def is_closed(self) -> bool:
        return getattr(self.request, '_closed', False)

    def receive(self, data: bytes = b'') -> bytes:
        while not self.is_closed:
            try:
                part = self.request.recv(1024)
            except ConnectionError as error:
                self.error('connection error: %s' % error)
                part = None
            if part is None:
                self.error('failed to receive data: %s %s' % (self.remote_user, self.client_address))
                break
            data += part
            if len(part) < 1024:
                break
        return data

    def send(self, data: bytes) -> bool:
        length = len(data)
        count = 0
        while count < length and not self.is_closed:
            self.request.settimeout(20)  # socket timeout for sending data
            try:
                count = self.request.send(data)
            except ConnectionError as error:
                self.error('connection error: %s' % error)
            self.request.settimeout(self.timeout)
            if count == 0:
                self.error('failed to send data: %s %s' % (self.remote_user, self.client_address))
                self.error('remaining data (%d): %s' % (len(data), data))
                return False
            if count == len(data):
                # all data sent
                return True
            data = data[count:]
            length = len(data)
            count = 0

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        if self.__push_data(body=data):
            if handler is not None:
                handler.success()
            return True
        else:
            if handler is not None:
                error = IOError('MessengerDelegate error: failed to send data package')
                handler.failed(error=error)
            return False

    def upload_data(self, data: bytes, msg: InstantMessage) -> str:
        # upload encrypted file data
        pass

    def download_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        # download encrypted file data
        pass
