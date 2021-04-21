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

import socket
import threading
import time
from typing import Optional

from ...utils import Logging

from .handler import ConnectionHandler, ConnectionDelegate
from .handler import JSONHandler, WebSocketHandler, MarsHandler, MTPHandler


class Connection(threading.Thread, Logging):

    def __init__(self):
        super().__init__()
        self.__started = False
        self.__running = False
        self.__handler: Optional[ConnectionHandler] = None
        self.__delegate: Optional[ConnectionDelegate] = None
        # locks
        self.__receive_lock = threading.Lock()
        self.__send_lock = threading.Lock()

    @property
    def delegate(self) -> ConnectionDelegate:
        return self.__delegate

    @delegate.setter
    def delegate(self, callback: ConnectionDelegate):
        self.__delegate = callback

    def set_handler(self, handler: ConnectionHandler):
        self.__handler = handler

    def get_handler(self, data: Optional[bytes] = b'') -> ConnectionHandler:
        """
        Process received data stream

        :param data: data stream
        :return: data package, data remaining
        """
        if self.__handler is None and len(data) > 0:
            # check data protocols
            if data.startswith(b'{"'):
                # Protocol 0: raw data (JSON in line)?
                self.set_handler(handler=JSONHandler())
            elif MarsHandler.parse_head(stream=data) is not None:
                # Protocol 1: Tencent mars?
                self.set_handler(handler=MarsHandler())
            elif MTPHandler.parse_head(stream=data) is not None:
                # Protocol 2: MTP?
                self.set_handler(handler=MTPHandler())
            elif WebSocketHandler.is_handshake(stream=data):
                # Protocol 3: Web Socket
                self.set_handler(handler=WebSocketHandler())
            else:
                # unknown protocol
                self.error('data stream error: %s' % data)
        return self.__handler

    #
    #   Socket
    #

    def get_socket(self) -> socket.socket:
        """ get connected socket """
        raise NotImplemented

    @property
    def is_closed(self) -> bool:
        sock = self.get_socket()
        if sock is None:
            return True
        else:
            return getattr(sock, '_closed', False)

    def receive(self) -> Optional[bytes]:
        with self.__receive_lock:
            sock = self.get_socket()
            if sock is None:
                return None
            try:
                return sock.recv(1024)
            except socket.error as error:
                self.error('failed to receive data: %s' % error)
                return None

    def sendall(self, data: bytes) -> bool:
        with self.__send_lock:
            sock = self.get_socket()
            if sock is None:
                return False
            try:
                sock.sendall(data)
                return True
            except socket.error as error:
                self.error('failed to send data: %s' % error)
                return False

    def send_data(self, payload: bytes) -> bool:
        handler = self.get_handler(data=payload)
        if handler is None:
            self.error('connection handler not ready')
            return False
        else:
            pack = handler.connection_pack(connection=self, data=payload)
            return self.sendall(data=pack)

    #
    #   Main
    #

    def start(self):
        tick = 0
        while self.__running:
            # waiting for last run loop exit
            time.sleep(0.1)
            tick += 1
            if tick > 100:
                # timeout (10 seconds)
                break
        # do start
        if not self.__started:
            super().start()

    def stop(self):
        self.__started = False

    def run(self):
        """ Run loop for receiving data """
        self.__started = True
        self.__running = True
        # start running
        while self.__started:
            # receive all data
            data = self.receive()
            if data is None:
                self.info('no more data, exit')
                break
            # process received data by connection handler
            handler = self.get_handler(data=data)
            if handler is not None:
                left = handler.connection_process(self, stream=data)
                # NOTICE: the handler process one package one time,
                #         so here must check whether more package(s) left,
                #         if true, try to process them.
                cnt = 16
                while left and cnt > 0:
                    left = handler.connection_process(self, stream=b'')
                    cnt -= 1
        # stop running
        self.__running = False
