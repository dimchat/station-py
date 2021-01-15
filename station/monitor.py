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

from dimp import ID
from dimp import TextContent
from dimp import Envelope, InstantMessage

from libs.utils import Log
from libs.common import Database
from libs.server import ServerMessenger
from libs.server import SessionServer
from libs.server import ApplePushNotificationService
from libs.server import ServerFacebook


class Monitor:

    def __init__(self):
        super().__init__()
        self.apns: ApplePushNotificationService = None
        self.session_server: SessionServer = None
        # message from the station to administrator(s)
        self.sender: ID = None
        self.admins: set = set()
        self.__messenger: ServerMessenger = None

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def messenger(self) -> ServerMessenger:
        if self.__messenger is None:
            m = ServerMessenger()
            m.barrack = self.facebook
            self.__messenger = m
        return self.__messenger

    @property
    def facebook(self) -> ServerFacebook:
        return ServerFacebook()

    @property
    def database(self) -> Database:
        return self.facebook.database

    def report(self, message: str) -> int:
        success = 0
        for receiver in self.admins:
            if self.send_report(text=message, receiver=receiver):
                success = success + 1
        return success

    def send_report(self, text: str, receiver: ID) -> bool:
        if self.sender is None:
            self.error('sender not set yet')
            return False
        timestamp = int(time.time())
        content = TextContent(text=text)
        env = Envelope.create(sender=self.sender, receiver=receiver, time=timestamp)
        i_msg = InstantMessage.create(head=env, body=content)
        s_msg = self.messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to report: %s, %s' % (receiver, text)
        r_msg = self.messenger.sign_message(msg=s_msg)
        if r_msg.delegate is None:
            r_msg.delegate = self.messenger
        # try for online user
        sessions = self.session_server.all(identifier=receiver)
        if sessions and len(sessions) > 0:
            self.info('%s is online(%d), try to push report: %s' % (receiver, len(sessions), text))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    # self.info('session invalid %s' % sess)
                    continue
                request_handler = self.session_server.get_handler(client_address=sess.client_address)
                if request_handler is None:
                    self.error('handler lost: %s' % sess)
                    continue
                if request_handler.push_message(r_msg):
                    success = success + 1
                else:
                    self.error('failed to push report via connection (%s, %s)' % sess.client_address)
            if success > 0:
                self.info('report pushed to activated session(%d) of user: %s' % (success, receiver))
                return True
        # store in local cache file
        self.info('%s is offline, store report: %s' % (receiver, text))
        self.database.store_message(r_msg)
        # push notification
        return self.apns.push(identifier=receiver, message=text)
