# -*- coding: utf-8 -*-

"""
    Android Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    C2DM / FCM

    A service for pushing notification to offline device
"""

from typing import Optional

import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

from dimples import ID

from ..utils import Logging
from ..common import PushInfo
from ..database import DeviceInfo

from .manager import PushNotificationService


class AndroidPushNotificationService(PushNotificationService, Logging):

    def __init__(self, cert: str):
        super().__init__()
        self.__cert = cert
        self.__ready = False

    def _check_ready(self) -> bool:
        if self.__ready:
            return True
        cert = self.__cert
        if cert is None or len(cert) == 0:
            return False
        else:
            # only init once
            self.__cert = None
        self.info(msg='initializing FCM client: %s' % cert)
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
        self.__ready = True
        return True

    def send_notification(self, notification, token: str):
        try:
            if not self._check_ready():
                self.error(msg='FCM client not ready')
                return None
            message = messaging.Message(
                notification=notification,
                token=token,
            )
            return messaging.send(message)
        except Exception as e:
            self.error(msg='failed to push notification: %s' % e)

    def send_message(self, title: str, body: str, image: Optional[str], token: str):
        responses = self.send_notification(notification=messaging.Notification(
            title=title,
            body=body,
            image=image
        ), token=token)
        self.info(msg='message "%s" sent, respond: %s' % (title, responses))
        return responses

    #
    #   PushService
    #

    # Override
    async def push_notification(self, aps: PushInfo, device: DeviceInfo, receiver: ID) -> bool:
        # 1. check parameters
        title = aps.title
        content = aps.content
        image = aps.image
        # 2. check channel
        channel = device.channel
        platform = device.platform
        if platform is None or platform.lower() != 'android':
            self.warning(msg='It is not an Android device, skip it: %s, %s' % (platform, receiver))
            return False
        elif channel is None or channel.lower() != 'firebase':
            self.warning(msg='C2DM channel not support yet: %s, %s' % (channel, receiver))
            return False
        token = device.token
        res = self.send_message(title=title, body=content, image=image, token=token)
        return res is not None
