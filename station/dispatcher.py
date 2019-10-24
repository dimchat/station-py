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

from typing import Optional

from mkm import is_broadcast
from dimp import ContentType, ReliableMessage

from libs.common import Database, Facebook, Log
from libs.server import ApplePushNotificationService, SessionServer


class Dispatcher:

    def __init__(self):
        super().__init__()
        self.database: Database = None
        self.facebook: Facebook = None
        self.session_server: SessionServer = None
        self.apns: ApplePushNotificationService = None
        self.neighbors: list = []

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def transmit(self, msg: ReliableMessage) -> bool:
        # TODO: broadcast to neighbor stations
        self.info('transmit to neighbors %s - %s' % (self.neighbors, msg))
        return False

    def broadcast(self, msg: ReliableMessage) -> bool:
        # TODO: split for all users
        self.info('broadcast message %s' % msg)
        return False

    def deliver(self, msg: ReliableMessage) -> bool:
        receiver = self.facebook.identifier(msg.envelope.receiver)
        if is_broadcast(identifier=receiver):
            return self.broadcast(msg=msg)
        # try for online user
        sessions = self.session_server.search(identifier=receiver)
        if sessions and len(sessions) > 0:
            self.info('%s is online(%d), try to push message: %s' % (receiver, len(sessions), msg.envelope))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    self.info('session invalid %s' % sess)
                    continue
                if sess.request_handler.push_message(msg):
                    success = success + 1
                else:
                    self.error('failed to push message via connection (%s, %s)' % sess.client_address)
            if success > 0:
                self.info('message pushed to activated session(%d) of user: %s' % (success, receiver))
                return True
        # store in local cache file
        self.info('%s is offline, store message: %s' % (receiver, msg.envelope))
        self.database.store_message(msg)
        # transmit to neighbor stations
        self.transmit(msg=msg)
        # push notification
        text = self.__push_msg(msg=msg)
        if text is not None:
            return self.apns.push(identifier=receiver, message=text)
        return True

    def __push_msg(self, msg: ReliableMessage) -> Optional[str]:
        msg_type = msg.envelope.type
        if msg_type == 0:
            something = 'something'
        elif msg_type == ContentType.Text:
            something = 'a text message'
        elif msg_type == ContentType.File:
            something = 'a file'
        elif msg_type == ContentType.Image:
            something = 'an image'
        elif msg_type == ContentType.Audio:
            something = 'a voice message'
        elif msg_type == ContentType.Video:
            something = 'a video message'
        else:
            Log.info('ignore msg type: %d' % msg_type)
            return None
        sender = self.facebook.identifier(msg.envelope.sender)
        receiver = self.facebook.identifier(msg.envelope.receiver)
        from_name = self.facebook.nickname(identifier=sender)
        to_name = self.facebook.nickname(identifier=receiver)
        text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
        # check group
        group = msg.envelope.group
        if group is not None:
            # group message
            gid = self.facebook.identifier(group)
            grp = self.facebook.group(identifier=gid)
            if grp is None:
                g_name = gid.name
            else:
                g_name = grp.name
            text = text + ' in group %s' % g_name
        # OK
        return text
