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

import socket
import traceback
from socketserver import StreamRequestHandler
from typing import Optional

from dimp import json_encode
from dimp import User
from dimp import InstantMessage, ReliableMessage
from dimsdk import CompletionHandler
from dimsdk import MessengerDelegate

from libs.utils import Logging
from libs.utils import NotificationCenter
from libs.common import NotificationNames
from libs.common import Connection, ConnectionDelegate, ConnectionHandler, DMTPHandler
from libs.common import CommonPacker
from libs.server import ServerMessenger, SessionServer, Session

from robots.nlp import chat_bots

from station.config import current_station


class ServerConnection(Connection):

    def __init__(self, request: socket.socket, handler):
        super().__init__()
        self.__request = request
        self.__handler = handler
        self.delegate = handler

    def set_handler(self, handler: ConnectionHandler):
        super().set_handler(handler=handler)
        if isinstance(handler, DMTPHandler):
            packer = self.__handler.messenger.packer
            assert isinstance(packer, CommonPacker), 'packer error: %s' % packer
            packer.mtp_format = packer.MTP_DMTP

    def get_socket(self) -> socket.socket:
        return self.__request

    def disconnect(self):
        if not self.is_closed:
            self.__request.close()
            self.__request = None

    def receive(self) -> Optional[bytes]:
        data = super().receive()
        if data is None:
            # connection lost
            self.disconnect()
        return data

    def sendall(self, data: bytes) -> bool:
        ok = super().sendall(data=data)
        if not ok:
            # connection lost
            self.disconnect()
        return ok


class RequestHandler(StreamRequestHandler, ConnectionDelegate, MessengerDelegate, Session.Handler, Logging):

    def __init__(self, request, client_address, server):
        self.__conn = ServerConnection(request=request, handler=self)
        # messenger
        self.__messenger: Optional[ServerMessenger] = None
        self.__session: Optional[Session] = None
        # init
        super().__init__(request=request, client_address=client_address, server=server)

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
    def remote_user(self) -> Optional[User]:
        if self.__messenger is not None:
            return self.__messenger.remote_user

    #
    #
    #
    def setup(self):
        super().setup()
        self.__session = SessionServer().get_session(client_address=self.client_address, handler=self)
        NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
            'session': self.__session,
        })
        self.info('client connected: %s' % self.__session)

    def finish(self):
        self.info('client disconnected: %s' % self.__session)
        NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
            'session': self.__session,
        })
        SessionServer().remove_session(session=self.__session)
        self.__session = None
        self.__messenger = None
        self.__conn.stop()
        super().finish()

    """
        DIM Request Handler
    """

    def handle(self):
        self.info('connection started: %s' % str(self.client_address))
        self.__conn.run()
        self.info('connection stopped: %s' % str(self.client_address))

    def push_message(self, msg: ReliableMessage) -> bool:
        body = json_encode(msg.dictionary)
        return self.__conn.send_data(payload=body)

    #
    #   ConnectionDelegate
    #
    def connection_received(self, connection, data: bytes) -> Optional[bytes]:
        if data.startswith(b'{'):
            # JsON in lines
            packages = data.splitlines()
        else:
            packages = [data]
        data = b''
        for pack in packages:
            try:
                res = self.messenger.process_package(data=pack)
                if res is not None and len(res) > 0:
                    data += res + b'\n'
            except Exception as error:
                self.error('parse message failed: %s' % error)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        # station MUST respond something to client request
        if len(data) > 0:
            data = data[:-1]  # remove last '\n'
        return data

    def connection_connected(self, connection):
        self.warning('connection connected: %s' % connection)

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        if self.__conn.send_data(payload=data):
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
