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

from dimp import ID
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ApplePushNotificationService

from ..common import Database
from ..common import Log

from .facebook import ServerFacebook
from .session import SessionServer


class Dispatcher:

    def __init__(self):
        super().__init__()
        self.database: Database = None
        self.facebook: ServerFacebook = None
        self.session_server: SessionServer = None
        self.apns: ApplePushNotificationService = None
        self.neighbors: list = []

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @staticmethod
    def __receipt(message: str, msg: ReliableMessage) -> Content:
        receipt = ReceiptCommand.new(message=message)
        for key in ['sender', 'receiver', 'time', 'group', 'signature']:
            value = msg.get(key)
            if value is not None:
                receipt[key] = value
        return receipt

    def __transmit(self, msg: ReliableMessage) -> bool:
        # TODO: broadcast to neighbor stations
        # receiver = msg.envelope.receiver
        # self.info('transmitting to neighbors %s, receiver: %s' % (self.neighbors, receiver))
        return False

    def __broadcast_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Deliver message to everyone@everywhere, including all neighbours """
        # TODO: broadcast this message
        self.info('broadcasting message %s' % msg)
        text = 'Message broadcast to "%s" is not implemented' % msg.envelope.receiver
        res = TextContent.new(text=text)
        res.group = msg.envelope.group
        return res

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        receiver = self.facebook.identifier(msg.envelope.receiver)
        if receiver.is_group:
            # group message (not split yet)
            if receiver.is_broadcast:
                # if it's a grouped broadcast id, then
                #    broadcast (split and deliver)to everyone
                return self.__broadcast_message(msg=msg)
            else:
                # let the assistant to process this group message
                assistants = self.facebook.assistants(receiver)
                if assistants is None or len(assistants) == 0:
                    raise LookupError('failed to get assistant for group: %s' % receiver)
                receiver = assistants[0]
        # try for online user
        sessions = self.session_server.all(identifier=receiver)
        if sessions and len(sessions) > 0:
            self.info('%s is online(%d), try to push message: %s' % (receiver, len(sessions), msg.envelope))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    # self.info('session invalid %s' % sess)
                    continue
                request_handler = self.session_server.get_handler(client_address=sess.client_address)
                if request_handler is None:
                    self.error('handler lost: %s' % sess)
                    continue
                if request_handler.push_message(msg):
                    success = success + 1
                else:
                    self.error('failed to push message via connection (%s, %s)' % sess.client_address)
            if success > 0:
                self.info('message pushed to activated session(%d) of user: %s' % (success, receiver))
                return self.__receipt(message='Message sent', msg=msg)
        # store in local cache file
        sender = self.facebook.identifier(msg.envelope.sender)
        group = self.facebook.identifier(msg.envelope.group)
        self.info('%s is offline, store message from: %s' % (receiver, sender))
        self.database.store_message(msg)
        # transmit to neighbor stations
        self.__transmit(msg=msg)
        # check mute-list
        if self.database.is_muted(sender=sender, receiver=receiver, group=group):
            self.info('this sender/group is muted: %s' % msg)
        else:
            # push notification
            msg_type = msg.envelope.type
            if msg_type is None:
                msg_type = 0
            self.__push_msg(sender=sender, receiver=receiver, group=group, msg_type=msg_type)
        # response
        return self.__receipt(message='Message delivering', msg=msg)

    def __push_msg(self, sender: ID, receiver: ID, group: ID, msg_type: int=0) -> bool:
        if msg_type == 0:
            something = 'a message'
        elif msg_type == ContentType.Text:
            something = 'a text message'
        elif msg_type == ContentType.File:
            something = 'a file'
        elif msg_type == ContentType.Image:
            something = 'an image'
        elif msg_type == ContentType.Audio:
            something = 'a voice message'
        elif msg_type == ContentType.Video:
            something = 'a video'
        else:
            self.info('ignore msg type: %d' % msg_type)
            return False
        from_name = self.facebook.nickname(identifier=sender)
        to_name = self.facebook.nickname(identifier=receiver)
        text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
        # check group
        if group is not None:
            # group message
            text += ' in group [%s]' % self.facebook.group_name(identifier=group)
        # push it
        self.info('APNs message: %s' % text)
        return self.apns.push(identifier=receiver, message=text)
