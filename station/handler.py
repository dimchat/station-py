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

from dimp import User
from dimp import InstantMessage
from dimsdk import CompletionHandler
from dimsdk import MessengerDelegate
from dimsdk.messenger import MessageCallback

from libs.utils import Logging
from libs.utils import NotificationCenter
from libs.stargate import GateStatus, GateDelegate, StarGate
from libs.common import NotificationNames
from libs.server import ServerMessenger, SessionServer, Session

from robots.nlp import chat_bots

from station.config import current_station


class RequestHandler(StreamRequestHandler, GateDelegate, MessengerDelegate, Logging):

    def __init__(self, request, client_address, server):
        self.__gate = StarGate(delegate=self)
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
        self.__gate.open(sock=self.request)
        self.__session = SessionServer().get_session(client_address=self.client_address, messenger=self.messenger)
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
        self.__gate.close()
        super().finish()

    """
        DIM Request Handler
    """

    def handle(self):
        self.info('connection started: %s' % str(self.client_address))
        self.__gate.process()
        self.info('connection stopped: %s' % str(self.client_address))

    #
    #   GateDelegate
    #
    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        self.warning('connection connected: %s' % gate.connection)
        if new_status == GateStatus.Error:
            # self.__session.flush()
            pass

    def gate_received(self, gate, payload: bytes) -> Optional[bytes]:
        if payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        else:
            packages = [payload]
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

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        delegate = None
        if isinstance(handler, MessageCallback):
            callback = handler.callback
            if isinstance(callback, GateDelegate):
                delegate = callback
        if self.__gate.send(payload=data, delegate=delegate):
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
