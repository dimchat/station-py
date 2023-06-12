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
import time
from abc import ABC, abstractmethod
from typing import Optional, Union, Tuple, Set, Dict

from dimples import ID, ReliableMessage
from dimples.server import PushCenter
from dimples.database.dos.base import template_replace

from ..utils import Singleton, Logging
from ..utils import Runner
from ..common import CommonFacebook
from ..database import Storage


class Recorder(ABC):

    @abstractmethod
    def flush(self, config: Dict):
        """ save records into local storage """
        raise NotImplemented


class Event(ABC):

    @abstractmethod
    def handle(self, config: Dict, recorder: Recorder):
        """ handle the event """
        raise NotImplemented


@Singleton
class Monitor(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__config: Optional[Dict] = None
        self.__facebook: Optional[CommonFacebook] = None
        self.__events = []
        self.__lock = threading.Lock()
        # records
        self.__active_recorder = ActiveRecorder()
        self.__msg_recorder = MessageRecorder()
        self.__flush_expired = 0
        self.start()

    @property
    def config(self) -> Dict:
        return self.__config

    @config.setter
    def config(self, info: Dict):
        assert isinstance(info, dict), 'monitor config error: %s' % info
        self.__config = info

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
        event = self.next()
        if event is None:
            # nothing to do now, return False to let the thread have a rest
            now = time.time()
            if self.__flush_expired < now:
                self.__flush_expired = now + 120
                self.__flush(config=self.config)
            return False
        # get recorder
        if isinstance(event, ActiveEvent):
            recorder = self.__active_recorder
        elif isinstance(event, MessageEvent):
            recorder = self.__msg_recorder
        else:
            self.error(msg='event error: %s' % event)
            return True
        # try to handle event with recorder
        try:
            event.handle(config=self.config, recorder=recorder)
        except Exception as e:
            self.error(msg='task error: %s' % e)
        finally:
            return True

    def __flush(self, config: Dict):
        try:
            self.__active_recorder.flush(config=config)
            self.__msg_recorder.flush(config=config)
        except Exception as error:
            self.error(msg='flush record error: %s' % error)

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

    # noinspection PyMethodMayBeStatic
    def __masters(self, config: Dict) -> Set[ID]:
        masters = config.get('masters')
        if isinstance(masters, str):
            masters = masters.split(',')
        else:
            return set()
        array = set()
        for item in masters:
            mid = ID.parse(identifier=item.strip())
            if mid is not None:
                array.add(mid)
        return array

    def __notice_master(self, config: Dict):
        identifier = self.sender
        monitor = Monitor()
        # build notification
        name = monitor.nickname(identifier=identifier)
        if name is None:
            name = str(identifier)
        else:
            name = '%s (%s)' % (identifier, name)
        if self.online:
            title = 'Activity: Online'
            text = '%s is online, socket %s' % (name, self.remote_address)
        else:
            title = 'Activity: Offline'
            text = '%s is offline, socket %s' % (name, self.remote_address)
        # push notification
        sender = ID.parse(identifier='monitor@anywhere')
        masters = self.__masters(config=config)
        self.warning(msg='notice masters %s: %s' % (masters, text))
        center = PushCenter()
        for receiver in masters:
            center.add_notification(sender=sender, receiver=receiver, title=title, content=text)

    # Override
    def handle(self, config: Dict, recorder: Recorder):
        self.__notice_master(config=config)
        assert isinstance(recorder, ActiveRecorder), 'recorder error: %s' % recorder
        sender = self.sender
        when = self.when
        online = self.online
        recorder.increase_counter(sender_type=sender.type, when=when, online=online)


class ActiveRecorder(Recorder):

    def __init__(self):
        super().__init__()
        self.__stat = {}
        self.__path = None

    def increase_counter(self, sender_type: int, when: float, online: Union[bool, int]):
        if isinstance(online, bool):
            online = int(online)
        # get data list for current hour
        now = time.localtime(when)
        hour = time.strftime('%Y-%m-%d %H', now)
        array = self.__stat.get(hour)
        if array is None:
            array = []
            self.__stat[hour] = array
        # get data record
        record = None
        for item in array:
            if item.get('sender_type') == sender_type and item.get('online') == online:
                # got it
                record = item
                break
        # increase counter
        if record is None:
            # create new record
            record = {
                'sender_type': sender_type,
                'online': online,
                'count': 1,
            }
            array.append(record)
        else:
            # update old record
            count = record.get('count')
            record['count'] = 1 if count is None else count + 1

    # Override
    def flush(self, config: Dict):
        # get file path
        path = config.get('online_stat')
        assert isinstance(path, str), 'online stat file path not found: %s' % config
        now = time.gmtime()
        path = template_replace(path, 'yyyy', str(now.tm_year))
        path = template_replace(path, 'mm', two_digit(value=now.tm_mon))
        path = template_replace(path, 'dd', two_digit(value=now.tm_mday))
        if self.__path is None:
            self.__path = path
        elif self.__path != path:
            # FIXME: it's the next day now, save the increased values
            self.__stat = {}
            self.__path = None
            return False
        # save data
        Storage.write_json(container=self.__stat, path=path)


class MessageEvent(Event):

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.msg = msg

    # Override
    def handle(self, config: Dict, recorder: Recorder):
        assert isinstance(recorder, MessageRecorder), 'recorder error: %s' % recorder
        sender = self.msg.sender
        msg_type = self.msg.type
        recorder.increase_counter(sender_type=sender.type, msg_type=msg_type)


class MessageRecorder(Recorder):

    def __init__(self):
        super().__init__()
        self.__stat = {}
        self.__path = None

    def increase_counter(self, sender_type: int, msg_type: Optional[int]):
        if msg_type is None:
            msg_type = 0
        # get data list for current hour
        now = time.localtime()
        hour = time.strftime('%Y-%m-%d %H', now)
        array = self.__stat.get(hour)
        if array is None:
            array = []
            self.__stat[hour] = array
        # get data record
        record = None
        for item in array:
            if item.get('sender_type') == sender_type and item.get('msg_type') == msg_type:
                # got it
                record = item
                break
        # increase counter
        if record is None:
            # create new record
            record = {
                'sender_type': sender_type,
                'msg_type': msg_type,
                'count': 1,
            }
            array.append(record)
        else:
            # update old record
            count = record.get('count')
            record['count'] = 1 if count is None else count + 1

    # Override
    def flush(self, config: Dict):
        # get file path
        path = config.get('msg_stat')
        assert isinstance(path, str), 'msg stat file path not found: %s' % config
        now = time.gmtime()
        path = template_replace(path, 'yyyy', str(now.tm_year))
        path = template_replace(path, 'mm', two_digit(value=now.tm_mon))
        path = template_replace(path, 'dd', two_digit(value=now.tm_mday))
        if self.__path is None:
            self.__path = path
        elif self.__path != path:
            # FIXME: it's the next day now, save the increased values
            self.__stat = {}
            self.__path = None
            return False
        # save data
        Storage.write_json(container=self.__stat, path=path)


def two_digit(value: int) -> str:
    if value < 10:
        return '0%s' % value
    else:
        return '%s' % value
