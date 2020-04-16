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
    Command Processor for 'login'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    login protocol
"""

from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimsdk import ReceiptCommand, LoginCommand
from dimsdk import CommandProcessor

from ...common import Log, Database


class LoginCommandProcessor(CommandProcessor):

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def database(self) -> Database:
        return self.get_context('database')

    @property
    def receptionist(self):
        return self.get_context('receptionist')

    def __is_roamer(self, cmd: LoginCommand):
        station = cmd.station
        sid = self.facebook.identifier(station.get('ID'))
        if sid is None:
            raise ValueError('login station error: %s' % station)
        # check whether the login station is current station
        current_station = self.get_context('station')
        if current_station is None:
            raise LookupError('current station not found')
        if current_station.identifier == sid:
            # skip it
            return False
        # TODO: check time expires
        return True

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(content, LoginCommand), 'command error: %s' % content
        # update login info
        if not self.database.save_login(cmd=content, sender=sender, msg=msg):
            return None
        # check roaming
        if self.__is_roamer(cmd=content):
            self.info('add roamer: %s -> %s' % (sender, content.station))
            self.receptionist.add_roamer(identifier=sender)
        # response
        self.info('login command: %s' % content)
        return ReceiptCommand.new(message='Login received')


# register
CommandProcessor.register(command='login', processor_class=LoginCommandProcessor)
