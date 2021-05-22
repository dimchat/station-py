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

from typing import Set, Dict

from dimp import ID

from ..utils import Singleton
from ..utils import NotificationCenter, NotificationObserver, Notification


class PushService:

    def push_notification(self, sender: ID, receiver: ID, message: str) -> bool:
        """
        Push Notification from sender to receiver

        :param sender:   sender ID
        :param receiver: receiver ID
        :param message:  notification text
        :return: False on error
        """
        raise NotImplemented


@Singleton
class NotificationPusher(PushService, NotificationObserver):

    def __init__(self):
        super().__init__()
        # push services
        self.__services: Set[PushService] = set()
        # counting offline messages
        self.__badges: Dict[ID, int] = {}
        # observing notifications
        nc = NotificationCenter()
        nc.add(observer=self, name='user_online')

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name='user_online')

    def add_service(self, service: PushService):
        self.__services.add(service)

    def get_badge(self, identifier: ID) -> int:
        num = self.__badges.get(identifier)
        if num is None:
            num = 1
        else:
            num += 1
        self.__badges[identifier] = num
        return num

    #
    #    Notification Observer
    #

    # Override
    def received_notification(self, notification: Notification):
        info = notification.info
        identifier = ID.parse(identifier=info.get('ID'))
        # clean badges with ID
        assert identifier is not None, 'notification error: %s' % info
        self.__badges.pop(identifier, None)

    #
    #   PushService
    #

    # Override
    def push_notification(self, sender: ID, receiver: ID, message: str) -> bool:
        sent = 0
        for service in self.__services:
            if service.push_notification(sender=sender, receiver=receiver, message=message):
                sent += 1
        return sent > 0
