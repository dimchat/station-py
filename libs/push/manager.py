# -*- coding: utf-8 -*-

"""
    Android Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""

import weakref
from abc import ABC, abstractmethod
from typing import Optional, List

from dimples import ID

from ..utils import Singleton, Logging
from ..common import PushInfo
from ..database import DeviceInfo


class PushNotificationService(ABC):

    @abstractmethod
    def push_notification(self, aps: PushInfo, device: DeviceInfo, receiver: ID) -> bool:
        raise NotImplemented


@Singleton
class PushNotificationClient(Logging):

    class Delegate(ABC):
        """
            APNs Delegate
            ~~~~~~~~~~~~~
        """

        @abstractmethod
        def devices(self, identifier: ID) -> Optional[List[DeviceInfo]]:
            """ get devices with token in hex format """
            pass

    def __init__(self):
        super().__init__()
        self.__apple: Optional[PushNotificationService] = None
        self.__android: Optional[PushNotificationService] = None
        # delegate to get device token
        self.__delegate: Optional[weakref.ReferenceType] = None  # APNs Delegate

    @property
    def apple_pns(self) -> Optional[PushNotificationService]:
        return self.__apple

    @apple_pns.setter
    def apple_pns(self, pns: PushNotificationService):
        self.__apple = pns

    @property
    def android_pns(self) -> Optional[PushNotificationService]:
        return self.__android

    @android_pns.setter
    def android_pns(self, pns: PushNotificationService):
        self.__android = pns

    @property
    def delegate(self) -> Delegate:
        if self.__delegate is not None:
            return self.__delegate()

    @delegate.setter
    def delegate(self, value: Delegate):
        self.__delegate = weakref.ref(value)

    def push_notification(self, aps: PushInfo, receiver: ID) -> bool:
        devices = self.delegate.devices(identifier=receiver)
        if devices is None or len(devices) == 0:
            self.warning('cannot get device token for user %s' % receiver)
            return False
        for item in devices:
            platform = item.platform
            if platform is None:
                self.error(msg='device error: %s => %s' % (item, receiver))
                continue
            platform = platform.lower()
            if platform == 'ios':
                pns = self.apple_pns
            elif platform == 'android':
                pns = self.android_pns
            else:
                self.error(msg='platform error: %s, %s => %s' % (platform, item, receiver))
                continue
            if pns is None:
                self.error(msg='push notification service not found: %s' % platform)
            elif pns.push_notification(aps=aps, device=item, receiver=receiver):
                self.info(msg='push notification success: %s' % receiver)
                return True
            else:
                self.error(msg='push notification error: %s' % receiver)
