# -*- coding: utf-8 -*-

"""
    Android Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""

import threading
import time
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List

from dimples import ID

from ..utils import Singleton, Logging, Runner
from ..common import PushInfo, PushItem
from ..database import DeviceInfo


class PushNotificationService(ABC):

    @abstractmethod
    def push_notification(self, aps: PushInfo, device: DeviceInfo, receiver: ID) -> bool:
        raise NotImplemented


class PushTask:

    EXPIRES = 300

    def __init__(self, items: List[PushItem], msg_time: float):
        super().__init__()
        self.__items = items
        self.__time = msg_time

    @property
    def items(self) -> List[PushItem]:
        return self.__items

    @property
    def is_expired(self) -> bool:
        now = time.time()
        return self.__time < (now - self.EXPIRES)


@Singleton
class PushNotificationClient(Runner, Logging):

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
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__apple: Optional[PushNotificationService] = None
        self.__android: Optional[PushNotificationService] = None
        # delegate to get device token
        self.__delegate: Optional[weakref.ReferenceType] = None  # APNs Delegate
        # push tasks
        self.__tasks: List[PushTask] = []
        self.__lock = threading.Lock()
        self.start()

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

    def add_task(self, items: List[PushItem], msg_time: float):
        task = PushTask(items=items, msg_time=msg_time)
        with self.__lock:
            self.__tasks.append(task)

    def __next_task(self) -> Optional[PushTask]:
        with self.__lock:
            if len(self.__tasks) > 0:
                return self.__tasks.pop(0)

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        task = self.__next_task()
        if task is None:
            # nothing to do now, return False to have a rest
            return False
        array = task.items
        if task.is_expired:
            self.warning(msg='task expired, drop %d item(s).' % len(array))
            array = []
        # push items
        for item in array:
            try:
                self.__push(aps=item.info, receiver=item.receiver)
            except Exception as error:
                self.error(msg='push error: %s, item: %s' % (error, item))
        return True

    def __push(self, aps: PushInfo, receiver: ID) -> bool:
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
