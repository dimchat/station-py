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

from typing import List

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimsdk import LoginCommand
from dimsdk.cpu import BaseCommandProcessor

from ...utils import Logging
from ...utils import NotificationCenter
from ...database import Database
from ...common import NotificationNames


g_database = Database()


class LoginCommandProcessor(BaseCommandProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, LoginCommand), 'command error: %s' % content
        # check roaming
        if not g_database.save_login(cmd=content, msg=msg):
            self.error('login command error/expired: %s' % content)
            return []
        sender = content.identifier
        station = content.station
        # assert isinstance(station, dict), 'login command error: %s' % cmd
        sid = ID.parse(identifier=station.get('ID'))
        self.info('user login: %s -> %s' % (sender, sid))
        # post notification: USER_ONLINE
        NotificationCenter().post(name=NotificationNames.USER_ONLINE, sender=self, info={
            'ID': str(sender),
            'station': str(sid),
            'time': content.time,
        })
        # check current station
        facebook = self.facebook
        # from ...common import CommonFacebook
        # assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        srv = facebook.current_user
        if sid == srv.identifier:
            # only respond the user login to this station
            text = 'Login received.'
            return self._respond_receipt(text=text)
        return []
