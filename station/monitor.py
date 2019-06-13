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
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""

import time

import dimp
from dimp.transceiver import transceiver

from .session import SessionServer
from .database import Database
from .apns import ApplePushNotificationService


class Monitor:

    def __init__(self):
        super().__init__()
        self.session_server: SessionServer = None
        self.database: Database = None
        self.transceiver: dimp.Transceiver = transceiver
        self.apns: ApplePushNotificationService = None
        # message from the station to administrator(s)
        self.sender: dimp.ID = None
        self.admins: set = set()

    def report(self, message: str) -> int:
        success = 0
        for receiver in self.admins:
            if self.send_report(text=message, receiver=receiver):
                success = success + 1
        return success

    def send_report(self, text: str, receiver: dimp.ID) -> bool:
        if self.sender is None:
            print('Monitor: sender not set yet')
            return False
        sender = dimp.ID(self.sender)
        receiver = dimp.ID(receiver)
        timestamp = int(time.time())
        content = dimp.TextContent.new(text=text)
        i_msg = dimp.InstantMessage.new(content=content, sender=sender, receiver=receiver, time=timestamp)
        r_msg = self.transceiver.encrypt_sign(i_msg)
        # try for online user
        sessions = self.session_server.search(identifier=receiver)
        if sessions and len(sessions) > 0:
            print('Monitor: %s is online(%d), try to push report: %s' % (receiver, len(sessions), text))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    print('Monitor: session invalid', sess)
                    continue
                if sess.request_handler.push_message(r_msg):
                    success = success + 1
                else:
                    print('Monitor: failed to push report via connection', sess.client_address)
            if success > 0:
                print('Monitor: report pushed to activated session(%d) of user: %s' % (success, receiver))
                return True
        # store in local cache file
        print('Monitor: %s is offline, store report: %s' % (receiver, text))
        self.database.store_message(r_msg)
        # push notification
        return self.apns.push(identifier=receiver, message=text)
