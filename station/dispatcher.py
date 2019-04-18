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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

import dimp

from .session import SessionServer
from .database import Database
from .apns import ApplePushNotificationService


class Dispatcher:

    def __init__(self):
        super().__init__()
        self.session_server: SessionServer = None
        self.database: Database = None
        self.apns: ApplePushNotificationService = None

    def deliver(self, msg: dimp.ReliableMessage) -> bool:
        receiver = msg.envelope.receiver
        receiver = dimp.ID(receiver)
        sessions = self.session_server.search(identifier=receiver)
        if sessions and len(sessions) > 0:
            print('Dispatcher: %s is online(%d), try to push message: %s' % (receiver, len(sessions), msg.envelope))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    print('Dispatcher: session invalid', sess)
                    continue
                if sess.request_handler.push_message(msg):
                    success = success + 1
                else:
                    print('Dispatcher: failed to push message via connection', sess.client_address)
            if success > 0:
                print('Dispatcher: message pushed to activated session(%d) of user: %s' % (success, receiver))
                return True
        # store in local cache file
        print('Dispatcher: %s is offline, store message: %s' % (receiver, msg.envelope))
        self.database.store_message(msg)
        # push notification
        account = self.database.account_create(identifier=receiver)
        account.delegate = self.database
        sender = msg.envelope.sender
        sender = dimp.ID(sender)
        contact = self.database.account_create(identifier=sender)
        contact.delegate = self.database
        text = 'Dear %s: %s sent you a message.' % (account.name, contact.name)
        return self.apns.push(identifier=receiver, message=text)
