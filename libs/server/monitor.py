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
from typing import Optional, Union, Tuple, List, Dict

from dimples import ID, ReliableMessage
from dimples import CustomizedContent
from dimples.server import PushCenter
from dimples.server import AnsCommandProcessor

from ..utils import Singleton, Log, Logging
from ..utils import Runner
from ..common import Config
from ..common import PushItem, PushCommand

from .emitter import Emitter


def get_emitter() -> Optional[Emitter]:
    monitor = Monitor()
    return monitor.emitter


def _get_nickname(identifier: ID) -> Optional[str]:
    emitter = get_emitter()
    if emitter is None:
        Log.error(msg='emitter not found')
        return None
    facebook = emitter.facebook
    if facebook is None:
        Log.warning(msg='facebook not found')
        return None
    name = None
    doc = facebook.document(identifier=identifier)
    if doc is not None:
        name = doc.name
    if name is None or len(name) == 0:
        return str(identifier)
    else:
        return '%s (%s)' % (identifier, name)


# TODO: temporary function, remove it after too many users online
def _notice_master(sender: ID, online: bool, remote_address: Tuple[str, int]):
    # get sender's name
    name = _get_nickname(identifier=sender)
    if online:
        title = 'Activity: Online'
        text = '%s is online, socket %s' % (name, remote_address)
    else:
        title = 'Activity: Offline'
        text = '%s is offline, socket %s' % (name, remote_address)
    # build notifications
    masters = '0x9527cFD9b6a0736d8417354088A4fC6e345E31F8'
    masters = _get_masters(value=masters)
    Log.warning(msg='notice masters %s: %s' % (masters, text))
    if len(masters) == 0:
        return False
    center = PushCenter()
    keeper = center.badge_keeper
    items = []
    for receiver in masters:
        badge = keeper.increase_badge(identifier=receiver)
        items.append(PushItem.create(receiver=receiver, title=title, content=text, badge=badge))
    # send to apns bot
    bot = AnsCommandProcessor.ans_id(name='apns')
    if bot is None:
        Log.error(msg='apns bot not found')
        return
    content = PushCommand(items=items)
    emitter = get_emitter()
    emitter.send_content(content=content, receiver=bot)
    Log.info(msg='push %d items to: %s' % (len(items), bot))


def _get_masters(value: str) -> List[ID]:
    text = value.replace(' ', '')
    if len(text) == 0:
        return []
    array = text.split(',')
    return ID.convert(array=array)


#
#   Event Recorder
#
class Recorder(ABC):

    @abstractmethod
    def extract(self) -> Union[List, Dict]:
        """ get and clear records """
        raise NotImplemented


class Event(ABC):

    @abstractmethod
    def handle(self, recorder: Recorder):
        """ handle the event """
        raise NotImplemented


@Singleton
class Monitor(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__events = []
        self.__lock = threading.Lock()
        self.__interval = 60  # seconds
        self.__next_time = 0
        # masters
        self.__users_listeners = []
        self.__stats_listeners = []
        # recorders
        self.__usr_recorder: Optional[Recorder] = None
        self.__msg_recorder: Optional[Recorder] = None
        # emitter to send message
        self.__emitter: Optional[Emitter] = None

    @property
    def emitter(self) -> Emitter:
        return self.__emitter

    @emitter.setter
    def emitter(self, delegate: Emitter):
        self.__emitter = delegate

    def _append_event(self, event: Event):
        with self.__lock:
            self.__events.append(event)

    def _next_event(self) -> Optional[Event]:
        with self.__lock:
            if len(self.__events) > 0:
                return self.__events.pop(0)

    def start(self, config: Config):
        # time interval
        interval = config.get_integer(section='monitor', option='interval')
        if interval > 0:
            self.__interval = interval
        self.__next_time = time.time() + self.__interval
        # listeners
        masters = config.get_string(section='monitor', option='users_listeners')
        if masters is not None:
            self.__users_listeners = _get_masters(value=masters)
        masters = config.get_string(section='monitor', option='stats_listeners')
        if masters is not None:
            self.__stats_listeners = _get_masters(value=masters)
        # create recorders
        self.__usr_recorder = ActiveRecorder()
        self.__msg_recorder = MessageRecorder()
        # start thread
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        # 1. check to flush data
        now = time.time()
        if now > self.__next_time:
            users = self.__usr_recorder.extract()
            stats = self.__msg_recorder.extract()
            try:
                self.__flush(users=users, stats=stats)
            except Exception as e:
                self.error(msg='flush data error: %s' % e)
            # flush next time
            self.__next_time = now + self.__interval
        # 2. check for next event
        event = self._next_event()
        if event is None:
            # nothing to do now, return False to let the thread have a rest
            return False
        try:
            self.__handle(event=event)
        except Exception as e:
            self.error(msg='handle event error: %s' % e)
        return True

    def __handle(self, event: Event):
        if isinstance(event, ActiveEvent):
            event.handle(recorder=self.__usr_recorder)
        elif isinstance(event, MessageEvent):
            event.handle(recorder=self.__msg_recorder)
        else:
            self.error(msg='event error: %s' % event)

    def __flush(self, users: List, stats: List):
        emitter = self.__emitter
        # send users data
        listeners = self.__users_listeners
        if len(listeners) > 0:
            content = CustomizedContent.create(app='chat.dim.monitor', mod='users', act='post')
            content['users'] = users
            for master in listeners:
                emitter.send_content(content=content, receiver=master)
        # send stats data
        listeners = self.__stats_listeners
        if len(listeners) > 0:
            content = CustomizedContent.create(app='chat.dim.monitor', mod='stats', act='post')
            content['stats'] = stats
            for master in listeners:
                emitter.send_content(content=content, receiver=master)

    #
    #   Events
    #

    def user_online(self, sender: ID, remote_address: Tuple[str, int]):
        event = ActiveEvent(sender=sender, remote_address=remote_address, online=True)
        self._append_event(event=event)

    def user_offline(self, sender: ID, remote_address: Tuple[str, int]):
        event = ActiveEvent(sender=sender, remote_address=remote_address, online=False)
        self._append_event(event=event)

    def message_received(self, msg: ReliableMessage):
        event = MessageEvent(msg=msg)
        self._append_event(event=event)


#
#   Event Handlers
#


class ActiveEvent(Event, Logging):

    def __init__(self, sender: ID, remote_address: Tuple[str, int], online: bool):
        super().__init__()
        self.__sender = sender
        self.__remote_address = remote_address
        self.__online = online

    # Override
    def handle(self, recorder: Recorder):
        assert isinstance(recorder, ActiveRecorder), 'recorder error: %s' % recorder
        sender = self.__sender
        recorder.add_user(identifier=sender)
        # TODO: temporary notification, remove after too many users online
        online = self.__online
        remote = self.__remote_address
        _notice_master(sender=sender, online=online, remote_address=remote)


class ActiveRecorder(Recorder):
    """
        Active users recorder
        ~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self):
        super().__init__()
        self.__users = set()

    def add_user(self, identifier: id):
        self.__users.add(identifier)

    # Override
    def extract(self) -> Union[List, Dict]:
        users = self.__users
        self.__users = set()
        return ID.revert(array=users)


class MessageEvent(Event):

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.msg = msg

    # Override
    def handle(self, recorder: Recorder):
        assert isinstance(recorder, MessageRecorder), 'recorder error: %s' % recorder
        sender = self.msg.sender
        msg_type = self.msg.type
        if msg_type is None:
            msg_type = 0
        recorder.increase_counter(sender_type=sender.type, msg_type=msg_type)


class MessageRecorder(Recorder):
    """
        Message stats recorder
        ~~~~~~~~~~~~~~~~~~~~~~

        'S' - Sender type
        'C' - Counter
        'U' - User ID (reserved)
        'T' - Message type
    """

    def __init__(self):
        super().__init__()
        self.__data = []

    def increase_counter(self, sender_type: int, msg_type: int):
        array = self.__data
        # get data record
        record = None
        for item in array:
            if item.get('S') == sender_type and item.get('T') == msg_type:
                # got it
                record = item
                break
        # increase counter
        if record is None:
            # create new record
            record = {
                'S': sender_type,
                'T': msg_type,
                'C': 1,
            }
            array.append(record)
        else:
            # update old record
            count = record.get('C')
            record['C'] = 1 if count is None else count + 1

    # Override
    def extract(self) -> Union[List, Dict]:
        array = self.__data
        self.__data = []
        return array
