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

import hashlib
import json
import struct
from socketserver import BaseRequestHandler
from typing import Optional

from dimp import User
from dimp import InstantMessage, ReliableMessage
from dimsdk import NetMsgHead, NetMsg, CompletionHandler
from dimsdk import MessengerDelegate

from libs.common import Log, base64_encode
from libs.server import Session
from libs.server import ServerMessenger
from libs.server import HandshakeDelegate

from .config import g_database, g_facebook, g_keystore, g_session_server
from .config import g_dispatcher, g_receptionist, g_monitor
from .config import current_station, station_name, chat_bot


class RequestHandler(BaseRequestHandler, MessengerDelegate, HandshakeDelegate):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # messenger
        self.__messenger: ServerMessenger = None
        # handlers with Protocol
        self.process_package = None
        self.push_data = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def chat_bots(self) -> list:
        bots = []
        # Tuling
        tuling = chat_bot('tuling')
        if tuling is not None:
            bots.append(tuling)
        # XiaoI
        xiaoi = chat_bot('xiaoi')
        if xiaoi is not None:
            bots.append(xiaoi)
        return bots

    @property
    def messenger(self) -> ServerMessenger:
        if self.__messenger is None:
            m = ServerMessenger()
            m.barrack = g_facebook
            m.key_cache = g_keystore
            m.dispatcher = g_dispatcher
            m.delegate = self
            # set context
            m.context['database'] = g_database
            m.context['session_server'] = g_session_server
            m.context['receptionist'] = g_receptionist
            m.context['bots'] = self.chat_bots
            m.context['handshake_delegate'] = self
            m.context['remote_address'] = self.client_address
            self.__messenger = m
        return self.__messenger

    @property
    def remote_user(self) -> Optional[User]:
        if self.__messenger is not None:
            return self.__messenger.remote_user

    #
    #
    #
    def setup(self):
        self.__messenger: ServerMessenger = None
        self.process_package = None
        self.push_data = None
        address = self.client_address
        self.info('set up with %s [%s]' % (address, station_name))
        g_session_server.set_handler(client_address=address, request_handler=self)
        g_monitor.report(message='Client connected %s [%s]' % (address, station_name))

    def finish(self):
        address = self.client_address
        user = self.remote_user
        if user is None:
            g_monitor.report(message='Client disconnected %s [%s]' % (address, station_name))
        else:
            nickname = g_facebook.nickname(identifier=user.identifier)
            session = g_session_server.get(identifier=user.identifier, client_address=address)
            if session is None:
                self.error('user %s not login yet %s %s' % (user, address, station_name))
            else:
                g_monitor.report(message='User %s logged out %s [%s]' % (nickname, address, station_name))
                # clear current session
                g_session_server.remove(session=session)
        # remove request handler fro session handler
        g_session_server.clear_handler(client_address=address)
        self.__messenger = None
        self.info('finish with %s %s' % (address, user))

    """
        DIM Request Handler
    """

    def handle(self):
        self.info('client connected (%s, %s)' % self.client_address)
        data = b''
        while current_station.running:
            # receive all data
            remaining_length = len(data)
            data = self.receive(data)
            if len(data) == remaining_length:
                self.info('no more data, exit %s, remaining=%d' % (self.client_address, remaining_length))
                break

            # check protocol
            while self.process_package is None:
                # (Protocol A) Web socket?
                if data.find(b'Sec-WebSocket-Key') > 0:
                    self.process_package = self.process_ws_handshake
                    self.push_data = self.push_ws_data
                    break

                # (Protocol B) Tencent mars?
                if self.parse_mars_head(data=data) is not None:
                    # OK, it seems be a mars package!
                    self.process_package = self.process_mars_package
                    self.push_data = self.push_mars_data
                    break

                # (Protocol C) raw data (JSON in line)?
                if data.startswith(b'{"') and data.find(b'\0') < 0:
                    self.process_package = self.process_raw_package
                    self.push_data = self.push_raw_data
                    break

                # unknown protocol
                data = b''
                # raise AssertionError('unknown protocol')
                break
            if self.process_package is None:
                continue

            # process package(s) one by one
            #    the received data packages maybe sticky
            n_len = len(data)
            o_len = n_len + 1
            while n_len < o_len:
                o_len = n_len
                data = self.process_package(data)
                n_len = len(data)

    #
    #   Protocol: WebSocket
    #
    ws_magic = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    ws_prefix = b'HTTP/1.1 101 Switching Protocol\r\n' \
                b'Server: DIM-Station\r\n' \
                b'Upgrade: websocket\r\n' \
                b'Connection: Upgrade\r\n' \
                b'WebSocket-Protocol: dimchat\r\n' \
                b'Sec-WebSocket-Accept: '
    ws_suffix = b'\r\n\r\n'

    def process_ws_handshake(self, pack: bytes):
        pos1 = pack.find(b'Sec-WebSocket-Key:')
        pos1 += len('Sec-WebSocket-Key:')
        pos2 = pack.find(b'\r\n', pos1)
        key = pack[pos1:pos2].strip()
        sec = hashlib.sha1(key + self.ws_magic).digest()
        sec = base64_encode(sec)
        res = self.ws_prefix + bytes(sec, 'UTF-8') + self.ws_suffix
        self.send(res)
        self.process_package = self.process_ws_package
        return b''

    # https://tools.ietf.org/html/rfc6455#section-5.2
    """
      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-------+-+-------------+-------------------------------+
     |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
     |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
     |N|V|V|V|       |S|             |   (if payload len==126/127)   |
     | |1|2|3|       |K|             |                               |
     +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
     |     Extended payload length continued, if payload len == 127  |
     + - - - - - - - - - - - - - - - +-------------------------------+
     |                               |Masking-key, if MASK set to 1  |
     +-------------------------------+-------------------------------+
     | Masking-key (continued)       |          Payload Data         |
     +-------------------------------- - - - - - - - - - - - - - - - +
     :                     Payload Data continued ...                :
     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
     |                     Payload Data continued ...                |
     +---------------------------------------------------------------+
    """
    def process_ws_package(self, pack: bytes):
        pack_len = len(pack)
        if pack_len < 2:
            return pack
        data = b''
        pos = 0
        while True:
            if pack_len < pos + 2:
                self.info('incomplete ws package for op code: %d' % pack_len)
                return pack
            # 1. check whether a continuation frame
            ch0 = pack[pos+0]
            # fin: indicates that this is the final fragment in a message.
            # op: 0 - denotes a continuation frame
            fin = ch0 >> 7
            op = ch0 & 0x0F
            # 2. get payload length
            ch1 = pack[pos+1]
            mask = ch1 >> 7
            msg_len = ch1 & 0x7F
            if msg_len == 126:
                if pack_len < pos + 4:
                    self.info('incomplete ws package for msg len: %d' % pack_len)
                    return pack
                b2 = pack[pos+2]
                b3 = pack[pos+3]
                msg_len = (b2 << 8) | b3
                pos += 4
            elif msg_len == 127:
                if pack_len < pos + 10:
                    self.info('incomplete ws package for msg len: %d' % pack_len)
                    return pack
                b2 = pack[pos+2]
                b3 = pack[pos+3]
                b4 = pack[pos+4]
                b5 = pack[pos+5]
                b6 = pack[pos+6]
                b7 = pack[pos+7]
                b8 = pack[pos+8]
                b9 = pack[pos+9]
                msg_len = b2 << 56 | b3 << 48 | b4 << 40 | b5 << 32 | b6 << 24 | b7 << 16 | b8 << 8 | b9
                pos += 10
            else:
                pos += 2
            # 3. get masking-key
            if mask == 1:
                if pack_len < pos + 4:
                    self.info('incomplete ws package for mask: %d' % pack_len)
                    return pack
                mask = pack[pos:pos+4]
                pos += 4
            else:
                mask = None
            # 4. get payload
            if pack_len < pos + msg_len:
                self.info('incomplete ws package for payload: %d' % pack_len)
                return pack
            payload = pack[pos:pos+msg_len]
            pos += msg_len
            if mask is None:
                content = payload
            else:
                content = ''
                for i, d in enumerate(payload):
                    content += chr(d ^ mask[i % 4])
                content = bytes(content, 'UTF-8')
            # 5. check op_code
            if op == 1:
                # TEXT
                data += content
            elif op == 2:
                # BINARY
                data += content
            elif op == 8:
                # TODO: CLOSE
                pass
            elif op == 9:
                # TODO: PING
                pass
            elif op == 10:
                # TODO: PONG
                pass
            else:
                self.error('ws op error: %d => %s' % (op, pack))
                return b''
            # 6. check final fragment
            if fin == 1:
                # cut the received package(s) and return the remaining
                pack = pack[pos:]
                break
        self.info('received ws package len: %d' % len(data))
        res = self.received_package(pack=data)
        self.push_ws_data(res)
        return pack

    def push_ws_data(self, body: bytes) -> bool:
        head = struct.pack('B', 129)
        msg_len = len(body)
        if msg_len < 126:
            head += struct.pack('B', msg_len)
        elif msg_len <= (2 ** 16 - 1):
            head += struct.pack('!BH', 126, msg_len)
        elif msg_len <= (2 ** 64 - 1):
            head += struct.pack('!BQ', 127, msg_len)
        else:
            raise ValueError('message is too long: %d' % msg_len)
        return self.send(head + body)

    #
    #   Protocol: Tencent mars
    #
    @staticmethod
    def parse_mars_head(data: bytes) -> Optional[NetMsgHead]:
        try:
            head = NetMsgHead(data)
            if head.version != 200:
                return None
            if head.cmd not in [head.SEND_MSG, head.NOOP]:
                return None
            # OK
            return head
        except ValueError:
            return None

    def process_mars_package(self, pack: bytes):
        # check package head
        if self.parse_mars_head(data=pack) is None:
            self.error('not a mars pack, drop it: %s' % pack)
            self.send(NetMsg(cmd=6, seq=0))
            return b''
        # try to get complete package
        try:
            mars = NetMsg(pack)
        except ValueError:
            # partially package? keep it for next loop
            return pack
        head = mars.head
        pack_len = head.head_length + head.body_length
        # cut sticky packages
        remaining = pack[pack_len:]
        pack = pack[:pack_len]
        # check cmd
        if head.cmd == head.SEND_MSG:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('messages not found')
            body = self.received_package(mars.body)
            res = NetMsg(cmd=head.cmd, seq=head.seq, body=body)
        elif head.cmd == head.NOOP:
            # TODO: handle NOOP request
            self.info('receive NOOP package, cmd=%d, seq=%d, package: %s' % (head.cmd, head.seq, pack))
            res = pack
        else:
            # TODO: handle Unknown request
            self.error('receive unknown package, cmd=%d, seq=%d, package: %s' % (head.cmd, head.seq, pack))
            res = NetMsg(cmd=6, seq=0)
        self.send(res)
        # return the remaining incomplete package
        return remaining

    def push_mars_data(self, body: bytes) -> bool:
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        data = NetMsg(cmd=10001, seq=0, body=body)
        return self.send(data)

    #
    #   Protocol: raw data (JSON string)
    #
    def process_raw_package(self, pack: bytes):
        # skip leading empty packages
        pack = pack.lstrip()
        if len(pack) == 0:
            # NOOP: heartbeat package
            self.info('respond <heartbeats>: %s' % pack)
            self.send(b'\n')
            return b''
        # check whether contain incomplete message
        pos = pack.rfind(b'\n')
        if pos < 0:
            # partially package? keep it for next loop
            return pack
        # maybe more than one message in a time
        res = self.received_package(pack[:pos])
        self.send(res)
        # return the remaining incomplete package
        return pack[pos+1:]

    def push_raw_data(self, body: bytes) -> bool:
        data = body + b'\n'
        return self.send(data=data)

    def push_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg)
        body = data.encode('utf-8')
        return self.push_data(body=body)

    #
    #   receive message(s)
    #
    def received_package(self, pack: bytes) -> Optional[bytes]:
        lines = pack.splitlines()
        body = b''
        for line in lines:
            line = line.strip()
            if len(line) == 0:
                self.info('ignore empty message')
                continue
            try:
                res = self.messenger.received_package(data=line)
                if res is None:
                    # station MUST respond something to client request
                    res = b''
                else:
                    res = res + b'\n'
            except Exception as error:
                self.error('parse message failed: %s' % error)
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
                res = b''
            body = body + res
        # all responses in one package
        return body

    #
    #   Socket IO
    #
    def receive(self, data: bytes=b'') -> bytes:
        while True:
            try:
                part = self.request.recv(1024)
            except IOError as error:
                self.error('failed to receive data %s' % error)
                part = None
            if part is None:
                break
            data += part
            if len(part) < 1024:
                break
        return data

    def send(self, data: bytes) -> bool:
        try:
            self.request.sendall(data)
            return True
        except IOError as error:
            self.error('failed to send data %s' % error)
            return False

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler) -> bool:
        if self.push_data(body=data):
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

    #
    #   HandshakeDelegate
    #
    def handshake_accepted(self, session: Session):
        sender = session.identifier
        session_key = session.session_key
        client_address = session.client_address
        user = g_facebook.user(identifier=sender)
        self.messenger.remote_user = user
        self.info('handshake accepted %s %s %s, %s' % (user.name, client_address, sender, session_key))
        g_monitor.report(message='User %s logged in %s %s' % (user.name, client_address, sender))
        # add the new guest for checking offline messages
        g_receptionist.add_guest(identifier=sender)

    def handshake_success(self):
        # TODO: broadcast 'login'
        pass
