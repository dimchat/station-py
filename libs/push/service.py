# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import threading
from typing import Set, Dict, List, Optional

from ipx import Singleton
from ipx import NotificationCenter, NotificationObserver, Notification

from dimp import ID
from startrek.fsm import Runner

from ..utils import Log


class PushService:

    def push_notification(self, sender: ID, receiver: ID, message: str, badge: Optional[int] = None) -> bool:
        """
        Push Notification from sender to receiver

        :param sender:   sender ID
        :param receiver: receiver ID
        :param message:  notification text
        :param badge:    offline messages count
        :return: False on error
        """
        raise NotImplemented


class PushInfo:

    def __init__(self, sender: ID, receiver: ID, message: str, badge: int):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.message = message
        self.badge = badge


@Singleton
class NotificationPusher(Runner, PushService, NotificationObserver):

    def __init__(self):
        super().__init__()
        # push services
        self.__services: Set[PushService] = set()
        # waiting list
        self.__queue: List[PushInfo] = []
        self.__badges: Dict[ID, int] = {}
        self.__lock = threading.Lock()
        # observing notifications
        nc = NotificationCenter()
        nc.add(observer=self, name='user_online')

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name='user_online')

    def add_service(self, service: PushService):
        """ add push notification service """
        self.__services.add(service)

    def __append(self, sender: ID, receiver: ID, message: str, badge: int):
        """ append push task to the waiting queue """
        with self.__lock:
            info = PushInfo(sender=sender, receiver=receiver, message=message, badge=badge)
            self.__queue.append(info)

    def __next(self) -> Optional[PushInfo]:
        """ next push task from the waiting queue """
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def __increase_badge(self, identifier: ID) -> int:
        """ get self-increasing badge """
        with self.__lock:
            num = self.__badges.get(identifier, 0) + 1
            self.__badges[identifier] = num
            return num

    def __clean_badge(self, identifier: ID):
        """ clear badge for user """
        with self.__lock:
            self.__badges.pop(identifier, None)

    #
    #    Notification Observer
    #

    # Override
    def received_notification(self, notification: Notification):
        info = notification.info
        identifier = ID.parse(identifier=info.get('ID'))
        # clean badges with ID
        if identifier is None:
            Log.error('notification error: %s' % notification)
        else:
            self.__clean_badge(identifier=identifier)

    #
    #   PushService
    #

    # Override
    def push_notification(self, sender: ID, receiver: ID, message: str, badge: Optional[int] = None) -> bool:
        if badge is None:
            # increase offline message counter
            badge = self.__increase_badge(identifier=receiver)
        self.__append(sender=sender, receiver=receiver, message=message, badge=badge)
        return True

    #
    #   Runner
    #

    def start(self):
        threading.Thread(target=self.run).start()

    # Override
    def process(self) -> bool:
        # get next info
        info = self.__next()
        if info is None:
            # nothing to do now, return False to have a rest
            return False
        else:
            sender = info.sender
            receiver = info.receiver
            message = info.message
            badge = info.badge
        # push via all services
        sent = 0
        for service in self.__services:
            if push(service=service, sender=sender, receiver=receiver, message=message, badge=badge):
                sent += 1
        return sent > 0


def push(service: PushService, sender: ID, receiver: ID, message: str, badge: int) -> bool:
    try:
        return service.push_notification(sender=sender, receiver=receiver, message=message, badge=badge)
    except Exception as error:
        print('Push Notification service error: %s' % error)
