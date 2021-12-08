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

from abc import ABC, abstractmethod
from typing import Optional

from ipx import SharedMemoryArrow

from dimp import json_encode, json_decode, utf8_encode, utf8_decode
from dimp import ID

from ..utils import Logging
from ..utils import Singleton
from ..utils import Notification, NotificationObserver, NotificationCenter


class PushArrow(SharedMemoryArrow):
    """ Half-duplex Pipe from station to pusher """

    # Station process IDs:
    #   0 - main
    #   1 - receptionist
    #   2 - pusher
    #   3 - monitor
    SHM_KEY = "D13502FF"

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    @classmethod
    def aim(cls):
        return cls.new(size=cls.SHM_SIZE, name=cls.SHM_KEY)


class PushService(ABC):

    @abstractmethod
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

    PUSHER_ID = ID.parse(identifier='pusher@anywhere')

    MSG_CLEAR_BADGE = 'CMD: CLEAR BADGE.'

    def __init__(self, sender: ID, receiver: ID, message: str, badge: Optional[int]):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.message = message
        self.badge = badge

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        return utf8_decode(data=json_encode(o={
            'sender': str(self.sender),
            'receiver': str(self.receiver),
            'message': self.message,
            'badge': self.badge,
        }))

    @classmethod
    def from_json(cls, string: str):
        info = json_decode(data=utf8_encode(string=string))
        return cls.from_dict(info=info)

    @classmethod
    def from_dict(cls, info: dict):
        sender = info.get('sender')
        receiver = info.get('receiver')
        message = info.get('message')
        badge = info.get('badge')
        if sender is not None and receiver is not None:
            sender = ID.parse(identifier=sender)
            receiver = ID.parse(identifier=receiver)
            return cls(sender=sender, receiver=receiver, message=message, badge=badge)


@Singleton
class PushCenter(PushService, NotificationObserver, Logging):

    def __init__(self):
        super().__init__()
        self.__arrow = PushArrow.aim()
        # observing local notifications
        nc = NotificationCenter()
        nc.add(observer=self, name='user_online')

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name='user_online')

    # Override
    def received_notification(self, notification: Notification):
        info = notification.info
        identifier = ID.parse(identifier=info.get('ID'))
        # clean badges with ID
        if identifier is None or notification.name != 'user_online':
            self.error('notification error: %s' % notification)
        else:
            receiver = PushInfo.PUSHER_ID
            message = PushInfo.MSG_CLEAR_BADGE
            self.push_notification(sender=identifier, receiver=receiver, message=message)

    # Override
    def push_notification(self, sender: ID, receiver: ID, message: str, badge: Optional[int] = None) -> bool:
        info = PushInfo(sender=sender, receiver=receiver, message=message, badge=badge)
        data = info.to_json()
        self.__arrow.send(obj=data)
        return True
