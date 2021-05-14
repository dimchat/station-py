# -*- coding: utf-8 -*-
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

import os
import threading
import time
import weakref
from typing import List, Optional

from dimp import json_encode, json_decode, utf8_encode, utf8_decode
from dimp import ID, NetworkType
from dimp import ReliableMessage

from .storage import Storage


def is_broadcast_message(msg: ReliableMessage):
    if msg.receiver.is_broadcast:
        return True
    group = msg.group
    return group is not None and group.is_broadcast


class MessageBundle:

    def __init__(self, db, identifier: ID):
        super().__init__()
        self.__db = weakref.ref(db)
        self.__identifier = identifier
        self.__messages: List[ReliableMessage] = []
        self.__lock = threading.Lock()

    def __del__(self):
        self.__flush()

    def __flush(self):
        db = self.__db()
        assert isinstance(db, MessageTable), 'db error: %s' % db
        while True:
            msg = self.pop()
            if msg is None:
                break
            db.save_message(msg=msg)

    def pop(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__messages) > 0:
                return self.__messages.pop(0)

    def add(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            signature = msg.get('signature')
            for item in self.__messages:
                if item.get('signature') == signature:
                    return False
            self.__messages.append(msg)
            return True

    def erase(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            signature = msg.get('signature')
            for item in self.__messages:
                if item.get('signature') == signature:
                    self.__messages.remove(item)
                    return True

    def all(self) -> List[ReliableMessage]:
        with self.__lock:
            db = self.__db()
            assert isinstance(db, MessageTable), 'db error: %s' % db
            messages = db.fetch_all_messages(receiver=self.__identifier)
            for msg in messages:
                exists = False
                signature = msg.get('signature')
                for item in self.__messages:
                    if item.get('signature') == signature:
                        exists = True
                        break
                if not exists:
                    self.__messages.append(msg)
            return self.__messages

    def count(self) -> int:
        messages = self.all()
        return len(messages)


class MessageTable(Storage):

    MESSAGE_EXPIRES = 3600 * 24 * 7  # only relay cached messages within 7 days

    def __init__(self):
        super().__init__()
        self.__bundles = weakref.WeakValueDictionary()  # ID -> MessageBundle
        self.__lock = threading.Lock()

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/dkd/{ADDRESS}/messages/*.msg'
        file path: '.dim/public/{ADDRESS}/messages/*.msg'
    """
    def __message_directory(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'messages')

    def __message_path(self, msg: ReliableMessage) -> str:
        # message filename
        timestamp = msg.time
        filename = time.strftime("%Y%m%d", time.localtime(timestamp))
        filename = filename + '.msg'
        # message directory
        directory = self.__message_directory(msg.receiver)
        # message file path
        return os.path.join(directory, filename)

    def __load_messages(self, path: str, remove: bool) -> List[ReliableMessage]:
        messages = []
        text = self.read_text(path=path)
        if text is None:
            lines = []
        else:
            if remove:
                self.remove(path=path)
            lines = text.splitlines()
        self.debug('read %d line(s) from %s' % (len(lines), path))
        expires = time.time() - self.MESSAGE_EXPIRES
        for line in lines:
            msg = line.strip()
            if len(msg) == 0:
                self.warning('skip empty line')
                continue
            try:
                msg = json_decode(data=utf8_encode(string=msg))
                msg = ReliableMessage.parse(msg=msg)
            except Exception as error:
                self.error('message package error %s, %s' % (error, line))
                continue
            if isinstance(msg, ReliableMessage):
                if msg.time < expires:
                    delta = time.time() - msg.time
                    days = delta / 3600 / 24
                    self.warning('drop expired msg: %d days ago, %s -> %s' % (days, msg.sender, msg.receiver))
                else:
                    messages.append(msg)
        return messages

    def __message_exists(self, msg: ReliableMessage, path: str) -> bool:
        if not self.exists(path=path):
            return False
        # check whether message duplicated
        messages = self.__load_messages(path=path, remove=False)
        for item in messages:
            if item.get('signature') == msg.get('signature'):
                # only same messages will have same signature
                return True

    def save_message(self, msg: ReliableMessage) -> bool:
        sender = msg.sender
        receiver = msg.receiver
        if is_broadcast_message(msg=msg):
            self.info('ignore broadcast msg: %s -> %s' % (sender, receiver))
            return False
        if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
            self.info('ignore station msg: %s -> %s' % (sender, receiver))
            return False
        path = self.__message_path(msg=msg)
        if self.__message_exists(msg=msg, path=path):
            self.error('msg duplicated: %s -> %s\n traces: %s\n signature: %s'
                       % (sender, receiver, msg.get('traces'), msg.get('signature')))
            return False
        self.debug('appending msg into: %s' % path)
        # message data
        data = utf8_decode(data=json_encode(msg.dictionary))
        data = data + '\n'
        return self.append_text(text=data, path=path)

    def fetch_all_messages(self, receiver: ID) -> List[ReliableMessage]:
        all_messages = []
        # message directory
        directory = self.__message_directory(receiver)
        # get all files in messages directory and sort by filename
        if self.exists(path=directory):
            files = sorted(os.listdir(directory))
        else:
            files = []
        for filename in files:
            if not filename.endswith('.msg'):
                continue
            # load messages from file path
            path = os.path.join(directory, filename)
            messages = self.__load_messages(path=path, remove=True)
            self.debug('got %d message(s) for %s in file: %s' % (len(messages), receiver, filename))
            for msg in messages:
                all_messages.append(msg)
        return all_messages

    def message_bundle(self, identifier: ID) -> MessageBundle:
        with self.__lock:
            bundle = self.__bundles.get(identifier)
            if bundle is None:
                bundle = MessageBundle(db=self, identifier=identifier)
                self.__bundles[identifier] = bundle
            return bundle

    def store_message(self, msg: ReliableMessage) -> bool:
        bundle = self.message_bundle(identifier=msg.receiver)
        return bundle.add(msg=msg)

    def erase_message(self, msg: ReliableMessage) -> bool:
        bundle = self.message_bundle(identifier=msg.receiver)
        return bundle.erase(msg=msg)
