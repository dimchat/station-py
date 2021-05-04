# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
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

import time
import weakref
from abc import abstractmethod
from typing import Optional

from .ship import Ship
from .starship import StarShip
from .docker import Docker
from .gate import Gate


"""
    Star Worker
    ~~~~~~~~~~~

    Processor for Star Ships
"""


class StarDocker(Docker):

    def __init__(self, gate: Gate):
        super().__init__()
        self.__gate = weakref.ref(gate)
        self.__running = False
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time()) + 2

    @property
    def gate(self) -> Gate:
        return self.__gate()

    #
    #   Running
    #

    def run(self):
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def stop(self):
        self.__running = False

    @property
    def working(self) -> bool:
        return self.__running and self.gate.opened

    # Override
    def setup(self):
        self.__running = True

    # Override
    def finish(self):
        # TODO: go through all outgo Ships parking in Dock and call 'sent failed' on their delegates
        self.__running = False

    # Override
    def handle(self):
        while self.working:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)

    # Override
    def process(self) -> bool:
        # 1. process income
        income = self._get_income_ship()
        if income is not None:
            res = self._process_income_ship(income=income)
            if res is not None:
                if res.priority == StarShip.SLOWER:
                    # put the response into waiting queue
                    self.gate.park_ship(ship=res)
                else:
                    # send response directly
                    self._send_outgo_ship(outgo=res)
        # 2. process outgo
        outgo = self._get_outgo_ship()
        if outgo is not None:
            if outgo.expired:
                # outgo Ship expired, callback
                delegate = outgo.delegate
                if delegate is not None:
                    delegate.ship_sent(ship=outgo, error=TimeoutError('Request timeout'))
            elif not self._send_outgo_ship(outgo=outgo):
                # failed to send outgo Ship, callback
                delegate = outgo.delegate
                if delegate is not None:
                    delegate.ship_sent(ship=outgo, error=IOError('Connection error'))
        # 3. heart beat
        if income is None and outgo is None:
            # check time for next heartbeat
            now = time.time()
            if now > self.__heartbeat_expired:
                if self.gate.expired:
                    beat = self._get_heartbeat()
                    if beat is not None:
                        # put the heartbeat into waiting queue
                        self.gate.park_ship(ship=beat)
                # try heartbeat next 2 seconds
                self.__heartbeat_expired = now + 2
            return False
        else:
            return True

    @abstractmethod
    def _get_income_ship(self) -> Optional[Ship]:
        """ Get income Ship from Connection """
        raise NotImplemented

    @abstractmethod
    def _process_income_ship(self, income: Ship) -> Optional[StarShip]:
        """ Override to process income Ship """
        linked = self._get_outgo_ship(income=income)
        if linked is None:
            return None
        # callback for the linked outgo Ship and remove it
        delegate = linked.delegate
        if delegate is not None:
            delegate.ship_sent(ship=linked)

    def _get_outgo_ship(self, income: Optional[Ship] = None) -> Optional[StarShip]:
        """ Get outgo Ship from waiting queue """
        if income is None:
            # get next new task (time == 0)
            outgo = self.gate.pull_ship()
            if outgo is None:
                # no more new task now, get any expired task
                outgo = self.gate.any_ship()
        else:
            # get task with ID
            outgo = self.gate.pull_ship(sn=income.sn)
        return outgo

    def _send_outgo_ship(self, outgo: StarShip) -> bool:
        """ Send outgo Ship via current Connection """
        return self.gate.send(data=outgo.package)

    def _get_heartbeat(self) -> Optional[StarShip]:
        """ Get an empty ship for keeping connection alive """
        pass
