# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List

from dimples import ID, ReliableMessage
from dimples.server import PushCenter

from ..utils import Singleton, Logging
from ..utils import Runner
from ..common import CommonFacebook


class Event(ABC):

    @abstractmethod
    def handle(self):
        """ handle the event """
        raise NotImplemented


@Singleton
class Monitor(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__facebook: Optional[CommonFacebook] = None
        self.__events = []
        self.__lock = threading.Lock()
        self.start()

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook

    @facebook.setter
    def facebook(self, barrack: CommonFacebook):
        self.__facebook = barrack

    def nickname(self, identifier: ID) -> Optional[str]:
        facebook = self.facebook
        if facebook is not None:
            doc = facebook.document(identifier=identifier)
            if doc is not None:
                return doc.name

    def append(self, event: Event):
        with self.__lock:
            self.__events.append(event)

    def next(self) -> Optional[Event]:
        with self.__lock:
            if len(self.__events) > 0:
                return self.__events.pop(0)

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        task = self.next()
        if task is None:
            # nothing to do now, return False to let the thread have a rest
            return False
        try:
            task.handle()
        except Exception as e:
            self.error(msg='task error: %s' % e)
        finally:
            return True

    #
    #   Events
    #

    def user_online(self, sender: ID, when: Optional[float], remote_address: Tuple[str, int]):
        event = ActiveEvent(sender=sender, when=when, remote_address=remote_address, online=True)
        self.append(event=event)

    def user_offline(self, sender: ID, when: Optional[float], remote_address: Tuple[str, int]):
        event = ActiveEvent(sender=sender, when=when, remote_address=remote_address, online=False)
        self.append(event=event)

    def message_received(self, msg: ReliableMessage):
        event = MessageEvent(msg=msg)
        self.append(event=event)

#
#   Event Handlers
#


class ActiveEvent(Event, Logging):

    def __init__(self, sender: ID, when: Optional[float], remote_address: Tuple[str, int], online: bool):
        super().__init__()
        self.sender = sender
        self.when = when
        self.remote_address = remote_address
        self.online = online

    # Override
    def handle(self):
        self.__notice_master()
        # TODO: record online/offline activity with sender.type and current time

    def __notice_master(self):
        identifier = self.sender
        monitor = Monitor()
        name = monitor.nickname(identifier=identifier)
        if name is None:
            name = str(identifier)
        else:
            name = '%s (%s)' % (identifier, name)
        if self.online:
            text = '%s is online' % name
        else:
            text = '%s is offline' % name
        #
        sender = ID.parse(identifier='monitor@anywhere')
        masters = self.__masters()
        self.warning(msg='notice masters %s: %s' % (masters, text))
        center = PushCenter()
        for receiver in masters:
            center.add_notification(sender=sender, receiver=receiver, title='Activity', content=text)

    # noinspection PyMethodMayBeStatic
    def __masters(self) -> List[ID]:
        # TODO: get master from station.ini
        master = ID.parse(identifier='0x9527cFD9b6a0736d8417354088A4fC6e345E31F8')
        return [master]


class MessageEvent(Event):

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.msg = msg

    # Override
    def handle(self):
        # TODO: record message count with sender.type, msg.type and current time
        pass
