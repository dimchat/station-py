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
from dimp import Content, Command
from dimsdk import LoginCommand, ReceiptCommand
from dimsdk import CommandProcessor

from ...utils import NotificationCenter, Logging
from ...common import NotificationNames
from ...common import Database, CommonFacebook


g_database = Database()


class LoginCommandProcessor(CommandProcessor, Logging):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, LoginCommand), 'command error: %s' % cmd
        sender = cmd.identifier
        # check roaming
        if not g_database.save_login(cmd=cmd, msg=msg):
            self.error('login command error/expired: %s' % cmd)
            return None
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        sid = ID.parse(identifier=station.get('ID'))
        self.info('user login: %s -> %s' % (sender, sid))
        # post notification: USER_ONLINE
        NotificationCenter().post(name=NotificationNames.USER_ONLINE, sender=self, info={
            'ID': sender,
            'station': sid,
        })
        # check current station
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        srv = facebook.current_user
        if sid == srv.identifier:
            # only respond the user login to this station
            return ReceiptCommand(message='Login received')


# register
CommandProcessor.register(command=Command.LOGIN, cpu=LoginCommandProcessor())
