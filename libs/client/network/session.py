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
from threading import Thread
from typing import Optional

from ...network import Hub, Gate, GateStatus

from ...common import BaseSession, CommonMessenger


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__(messenger=messenger, address=address, sock=sock)
        self.__key: Optional[str] = None
        self.__thread: Optional[Thread] = None

    @property  # Override
    def key(self) -> Optional[str]:
        return self.__key

    @key.setter
    def key(self, session: str):
        self.__key = session

    def start(self):
        self.__force_stop()
        t = Thread(target=self.run)
        self.__thread = t
        t.start()

    def __force_stop(self):
        keeper = self.keeper
        if keeper.running:
            keeper.stop()
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
            self.info('connection lost, reconnecting: remote = %s, local = %s' % (remote, local))
            hub = self.gate.hub
            assert isinstance(hub, Hub), 'hub error: %s' % hub
            hub.connect(remote=remote, local=local)
