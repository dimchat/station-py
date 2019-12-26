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

import json
from socketserver import BaseRequestHandler
from typing import Optional

from dimp import User
from dimp import InstantMessage, ReliableMessage
from dimsdk import NetMsgHead, NetMsg, CompletionHandler
from dimsdk import MessengerDelegate

from libs.common import Log
from libs.server import Session
from libs.server import ServerMessenger
from libs.server import HandshakeDelegate

from .config import g_database, g_facebook, g_keystore, g_session_server
from .config import g_dispatcher, g_receptionist, g_monitor
from .config import current_station, station_name, local_servers, chat_bot


class RequestHandler(BaseRequestHandler, MessengerDelegate, HandshakeDelegate):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # messenger
        self.__messenger: ServerMessenger = None

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
        address = self.client_address
        self.__messenger: ServerMessenger = None
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
            incomplete_length = len(data)
            while True:
                part = self.receive(1024)
                if part is None:
                    break
                data += part
                if len(part) < 1024:
                    break
            if len(data) == incomplete_length:
                self.info('no more data, exit (%d, %s)' % (incomplete_length, self.client_address))
                break

            # process package(s) one by one
            #    the received data packages maybe spliced,
            #    if the message data was wrap by other transfer protocol,
            #    use the right split char(s) to split it
            while len(data) > 0:

                # (Protocol A) Tencent mars?
                mars = False
                head = None
                try:
                    head = NetMsgHead(data=data)
                    if head.version == 200:
                        # OK, it seems be a mars package!
                        mars = True
                        self.push_data = self.push_mars_data
                except ValueError:
                    # self.error('not mars message pack: %s' % error)
                    pass
                # check mars head
                if mars:
                    self.info('@@@ msg via mars, len: %d+%d' % (head.head_length, head.body_length))
                    # check completion
                    pack_len = head.head_length + head.body_length
                    if pack_len > len(data):
                        # partially data, keep it for next loop
                        break
                    # cut out the first package from received data
                    pack = data[:pack_len]
                    data = data[pack_len:]
                    self.handle_mars_package(pack)
                    # mars OK
                    continue

                if data.startswith(b'\n'):
                    # NOOP: heartbeat package
                    self.info('trim <heartbeats>: %s' % data)
                    data = data.lstrip(b'\n')
                    continue

                # (Protocol B) raw data with no wrap?
                if data.startswith(b'{"') and data.find(b'\0') < 0:
                    # OK, it seems be a raw package!
                    self.push_data = self.push_raw_data
                    # check completion
                    pos = data.find(b'\n')
                    if pos < 0:
                        # partially data, keep it for next loop
                        break
                    # cut out the first package from received data
                    pack = data[:pos+1]
                    data = data[pos+1:]
                    self.handle_raw_package(pack)
                    # raw data OK
                    continue

                # (Protocol ?)
                # TODO: split and unwrap data package(s)
                self.error('unknown protocol %s' % data)
                data = b''
                # raise AssertionError('unknown protocol')

    #
    #   process and response message
    #
    def handle_mars_package(self, pack: bytes):
        pack = NetMsg(pack)
        head = pack.head
        if head.cmd == 3:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('messages not found')
            # maybe more than one message in a pack
            lines = pack.body.splitlines()
            body = b''
            for line in lines:
                if line.isspace():
                    self.info('ignore empty message')
                    continue
                response = self.process_package(line)
                if response:
                    body = body + response + b'\n'
            if body:
                data = NetMsg(cmd=head.cmd, seq=head.seq, body=body)
                # self.info('mars response %s' % data)
                self.send(data)
            else:
                # TODO: handle error message
                self.info('nothing to response, requests: %s' % lines)
        elif head.cmd == 6:
            # TODO: handle NOOP request
            self.info('receive NOOP package, response %s' % pack)
            self.send(pack)
        else:
            # TODO: handle Unknown request
            self.error('cmd=%d, seq=%d, package: %s' % (head.cmd, head.seq, pack))
            self.send(pack)

    def handle_raw_package(self, pack: bytes):
        response = self.process_package(pack)
        if response:
            data = response + b'\n'
            self.send(data)
        else:
            self.info('respond nothing')
            # self.send(pack)

    #
    #   push message
    #
    def push_mars_data(self, body: bytes) -> bool:
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        data = NetMsg(cmd=10001, seq=0, body=body)
        return self.send(data)

    def push_raw_data(self, body: bytes) -> bool:
        data = body + b'\n'
        return self.send(data=data)

    push_data = push_raw_data

    def push_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg)
        body = data.encode('utf-8')
        return self.push_data(body=body)

    #
    #   receive message
    #
    def process_package(self, pack: bytes) -> Optional[bytes]:
        try:
            res = self.messenger.received_package(data=pack)
            if res is None:
                # station MUST respond something to client request
                return b''
            return res
        except Exception as error:
            self.error('parse message failed: %s' % error)

    #
    #   Socket IO
    #
    def receive(self, buffer_size=1024) -> bytes:
        try:
            return self.request.recv(buffer_size)
        except IOError as error:
            self.error('failed to receive data %s' % error)

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
