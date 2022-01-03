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
    Station Server
    ~~~~~~~~~~~~~~

    Local station
"""

import socket
import traceback
from threading import Thread
from typing import Optional

from startrek import Connection
from startrek import Arrival

from ...network import Hub, Gate, GateStatus
from ...network import MTPStreamArrival

from ...common import BaseSession, CommonMessenger


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__(messenger=messenger, address=address, sock=sock)
        self.__key: Optional[str] = None
        self.__thread: Optional[Thread] = None

    @property
    def thread(self) -> Optional[Thread]:
        return self.__thread

    @property
    def server(self):
        messenger = self.messenger
        from ..messenger import ClientMessenger
        assert isinstance(messenger, ClientMessenger), 'client messenger error: %s' % messenger
        return messenger.server

    @property  # Override
    def key(self) -> Optional[str]:
        return self.__key

    @key.setter
    def key(self, session: str):
        self.__key = session

    def start(self):
        self.__force_stop()
        t = Thread(target=self.run, daemon=True)
        self.__thread = t
        t.start()

    def __force_stop(self):
        t: Thread = self.__thread
        if t is not None:
            # waiting 2 seconds for stopping the thread
            self.__thread = None
            t.join(timeout=2.0)

    # Override
    def stop(self):
        super().stop()
        self.__force_stop()

    # Override
    def setup(self):
        self.active = True
        super().setup()

    # Override
    def finish(self):
        self.active = False
        super().finish()

    #
    #   GateDelegate
    #

    # Override
    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            # clear session key
            server = self.server
            if server is not None:
                server.handshake_again()
            self.info('connection lost, reconnecting: remote = %s, local = %s' % (remote, local))
            # reconnect
            hub = self.gate.hub
            assert isinstance(hub, Hub), 'hub error: %s' % hub
            hub.connect(remote=remote, local=local)

    # Override
    def gate_received(self, ship: Arrival,
                      source: tuple, destination: Optional[tuple], connection: Connection):
        assert isinstance(ship, MTPStreamArrival), 'arrival ship error: %s' % ship
        payload = ship.payload
        # check payload
        if payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        else:
            packages = [payload]
        array = []
        messenger = self.messenger
        for pack in packages:
            try:
                responses = messenger.process_package(data=pack)
                for res in responses:
                    if res is None or len(res) == 0:
                        # should not happen
                        continue
                    array.append(res)
            except Exception as error:
                self.error('parse message failed (%s): %s, %s' % (source, error, pack))
                self.error('payload: %s' % payload)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        if len(array) == 0:
            return
        gate = self.gate
        for item in array:
            gate.send_response(payload=item, ship=ship, remote=source, local=destination)
