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
    Apple Push Notification service (APNs)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""

from abc import ABCMeta, abstractmethod

from apns2.client import APNsClient
from apns2.errors import APNsException
from apns2.payload import Payload


class ApplePushNotificationService:

    def __init__(self, credentials, use_sandbox=False, use_alternative_port=False, proto=None, json_encoder=None,
                 password=None, proxy_host=None, proxy_port=None):
        super().__init__()
        # APNs client
        self.client = APNsClient(credentials=credentials, use_sandbox=use_sandbox,
                                 use_alternative_port=use_alternative_port,
                                 proto=proto, json_encoder=json_encoder, password=password,
                                 proxy_host=proxy_host, proxy_port=proxy_port)
        # topic
        self.topic = 'chat.dim.sechat'
        # delegate to get device token
        self.delegate = None  # IAPNsDelegate

    def push(self, identifier: str, message: str, badge: int=1) -> bool:
        tokens = self.delegate.device_tokens(identifier=identifier)
        if tokens is None:
            return False
        success = 0
        for token in tokens:
            payload = Payload(alert=message, badge=badge, sound='default')
            try:
                self.client.send_notification(token_hex=token, notification=payload, topic=self.topic)
                success = success + 1
            except APNsException as error:
                print('failed to push notification: %s, error %s' % (message, error))
        return success > 0


class IAPNsDelegate(metaclass=ABCMeta):
    """
        APNs Delegate
        ~~~~~~~~~~~~~
    """

    @abstractmethod
    def device_tokens(self, identifier: str) -> list:
        """ get device tokens in hex format """
        pass
