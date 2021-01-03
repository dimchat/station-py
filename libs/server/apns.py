# -*- coding: utf-8 -*-
#
#   APNs : Apple Push Notification service
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Apple Push Notification service (APNs)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""

from abc import ABC, abstractmethod

from apns2.client import APNsClient, NotificationPriority
from apns2.errors import APNsException
from apns2.payload import Payload


class ApplePushNotificationService:

    def __init__(self, credentials, use_sandbox=False, use_alternative_port=False, proto=None, json_encoder=None,
                 password=None, proxy_host=None, proxy_port=None):
        super().__init__()
        # APNs client parameters
        self.credentials = credentials
        self.use_sandbox = use_sandbox
        self.use_alternative_port = use_alternative_port
        self.proto = proto
        self.json_encoder = json_encoder
        self.password = password
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.client = None  # APNsClient
        # topic
        self.topic = 'chat.dim.sechat'
        # delegate to get device token
        self.delegate = None  # IAPNsDelegate
        # counting offline messages
        self.badge_table = {}

    @staticmethod
    def info(msg: str):
        # Log.info('APNs:\t%s' % msg)
        pass

    @staticmethod
    def error(msg: str):
        # Log.error('APNs ERROR:\t%s' % msg)
        pass

    def badge(self, identifier: str) -> int:
        num = self.badge_table.get(identifier)
        if num is None:
            num = 1
        else:
            num = num + 1
        self.badge_table[identifier] = num
        return num

    def clear_badge(self, identifier: str) -> bool:
        if identifier in self.badge_table:
            self.badge_table.pop(identifier)
            return True

    def connect(self) -> bool:
        try:
            self.client = APNsClient(credentials=self.credentials, use_sandbox=self.use_sandbox,
                                     use_alternative_port=self.use_alternative_port,
                                     proto=self.proto, json_encoder=self.json_encoder, password=self.password,
                                     proxy_host=self.proxy_host, proxy_port=self.proxy_port)
            return True
        except IOError as error:
            self.error('failed to connect apple server: %s' % error)
            return False

    def send_notification(self, token_hex, notification, topic=None,
                          priority=NotificationPriority.Immediate, expiration=None, collapse_id=None) -> int:
        if self.client is None and self.connect() is False:
            self.error('cannot connect apple server, message dropped: %s' % notification)
            return -503  # Service Unavailable
        try:
            if topic is None:
                topic = self.topic
            # push to apple server
            self.client.send_notification(token_hex=token_hex, notification=notification, topic=topic,
                                          priority=priority, expiration=expiration, collapse_id=collapse_id)
            return 200  # OK
        except IOError as error:
            self.error('connection lost: %s' % error)
            return -408  # Request Timeout
        except APNsException as error:
            self.error('failed to push notification: %s, error %s' % (notification, error))
            return -400  # Bad Request

    def push(self, identifier: str, message: str) -> bool:
        # 1. check
        tokens = self.delegate.device_tokens(identifier=identifier)
        if tokens is None:
            self.error('cannot get device token for user %s' % identifier)
            return False
        # 2. send
        badge = self.badge(identifier)
        payload = Payload(alert=message, badge=badge, sound='default')
        success = 0
        for token in tokens:
            self.info('sending notification %s to user %s with token %s' % (message, identifier, token))
            # first try
            result = self.send_notification(token_hex=token, notification=payload)
            if result == -503:  # Service Unavailable
                # connection failed
                break
            elif result == -408:  # Request Timeout
                self.error('Broken pipe? try to reconnect again!')
                # reset APNs client
                self.client = None
                # try again
                result = self.send_notification(token_hex=token, notification=payload)
            if result == 200:  # OK
                success = success + 1
        if success > 0:
            self.info('sending notification success:%d badge=%d, %s' % (success, badge, identifier))
            return True


class IAPNsDelegate(ABC):
    """
        APNs Delegate
        ~~~~~~~~~~~~~
    """

    @abstractmethod
    def device_tokens(self, identifier: str) -> list:
        """ get device tokens in hex format """
        pass
