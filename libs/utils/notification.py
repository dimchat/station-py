# -*- coding: utf-8 -*-
#
#   LNC: Local Notification Center
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

from weakref import WeakSet
from abc import ABC, abstractmethod
from typing import Optional, Any


class Notification:
    """ Notification object with name, sender and extra info """

    def __init__(self, name: str, sender: Any, info: dict=None):
        super().__init__()
        self.__name = name
        self.__sender = sender
        self.__info = info

    @property
    def name(self) -> str:
        return self.__name

    @property
    def sender(self) -> Any:
        return self.__sender

    @property
    def info(self) -> Optional[dict]:
        return self.__info

    @info.setter
    def info(self, value: dict):
        self.__info = value


class Observer(ABC):
    """ Notification Observer """

    @abstractmethod
    def received_notification(self, notification: Notification):
        """
        Callback for notification

        :param notification: notification with name, sender and extra info
        :return:
        """
        pass


class NotificationCenter:
    """ Notification dispatcher """

    def __init__(self):
        super().__init__()
        self.__observers: dict = {}

    def add(self, observer: Observer, name: str):
        """
        Add observer with notification name

        :param observer: notification observer
        :param name:     notification name
        :return:
        """
        array: WeakSet = self.__observers.get(name)
        if array is None:
            array = WeakSet()
            self.__observers[name] = array
        else:
            # check duplicated
            for item in array:
                if item == observer:
                    # already exists
                    return
        array.add(observer)

    def __remove(self, observer: Observer, name: str):
        array: WeakSet = self.__observers.get(name)
        if array is None:
            return
        # check
        for item in array:
            if item == observer:
                # got it
                array.remove(item)
                break

    def remove(self, observer: Observer, name: str=None):
        """
        Remove observer from notification center, no mather what names

        :param observer: notification observer to remove
        :param name:     notification name (if empty, remove from all names)
        :return:
        """
        if name is None:
            keys = self.__observers.keys()
            for item in keys:
                self.__remove(observer=observer, name=item)
        else:
            self.__remove(observer=observer, name=name)

    def post(self, notification: Notification=None,
             name: str=None, sender: Any=None, info: dict=None):
        """
        Post a notification (with name, sender and extra info)

        :param notification: notification object
        :param name:         notification name  (when 'notification' empty)
        :param sender:       notification sender(when 'notification' empty)
        :param info:         extra info         (when 'notification' empty)
        :return:
        """
        if notification is None:
            assert name is not None, 'Notification name empty'
            assert sender is not None, 'Notification sender empty'
            notification = Notification(name=name, sender=sender, info=info)
        # temporary array buffer, used as a snapshot of the state of current observers
        array = self.__observers.get(notification.name)
        if array is not None:
            # call observers one by one
            for observer in array:
                observer.received_notification(notification=notification)

    @classmethod
    def default(cls):
        return default_center


#
#   Singleton
#
default_center = NotificationCenter()
