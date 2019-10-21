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

import json
import os
import time

from dimp import ID
from dimp import ReliableMessage

from .storage import Storage


class MessageTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        # self.__caches: dict = {}

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/dkd/{ADDRESS}/messages/*.msg'
        file path: '.dim/public/{ADDRESS}/messages/*.msg'
    """
    def __directory(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', identifier.address, 'messages')

    def __message_path(self, msg: ReliableMessage) -> str:
        # message filename
        timestamp = msg.envelope.time
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        filename = filename + '.msg'
        # message directory
        receiver = self.identifier(msg.envelope.receiver)
        directory = self.__directory(receiver)
        # message file path
        return os.path.join(directory, filename)

    def __load_messages(self, path: str) -> list:
        data = self.read_text(path=path)
        lines = data.splitlines()
        self.info('read %d line(s) from %s' % (len(lines), path))
        # messages = [ReliableMessage(json.loads(line)) for line in lines]
        messages = []
        for line in lines:
            msg = line.strip()
            if len(msg) == 0:
                self.info('skip empty line')
                continue
            try:
                msg = json.loads(msg)
                msg = ReliableMessage(msg)
                messages.append(msg)
            except Exception as error:
                self.info('message package error %s, %s' % (error, line))
        return messages

    def __message_exists(self, msg: ReliableMessage, path: str) -> bool:
        if not self.exists(path=path):
            return False
        # check whether message duplicated
        messages = self.__load_messages(path=path)
        for item in messages:
            if item.get('signature') == msg.get('signature'):
                # only same messages will have same signature
                return True

    def message_exists(self, msg: ReliableMessage) -> bool:
        path = self.__message_path(msg=msg)
        return self.__message_exists(msg=msg, path=path)

    def store_message(self, msg: ReliableMessage) -> bool:
        path = self.__message_path(msg=msg)
        if self.__message_exists(msg=msg, path=path):
            self.error('message duplicated: %s' % msg)
            return False
        self.info('Appending message into: %s' % path)
        # message data
        data = json.dumps(msg) + '\n'
        return self.append_text(text=data, path=path)

    def load_message_batch(self, receiver: ID) -> dict:
        # message directory
        directory = self.__directory(receiver)
        # get all files in messages directory and sort by filename
        if self.exists(path=directory):
            files = sorted(os.listdir(directory))
        else:
            files = []
        for filename in files:
            # read ONE .msg file for each receiver and remove the file immediately
            if filename[-4:] == '.msg':
                # load messages from file path
                path = os.path.join(directory, filename)
                messages = self.__load_messages(path=path)
                self.info('got %d message(s) for %s' % (len(messages), receiver))
                if len(messages) == 0:
                    self.info('remove empty message file %s' % path)
                    self.remove(path)
                return {'ID': receiver, 'filename': filename, 'path': path, 'messages': messages}

    def remove_message_batch(self, batch: dict, removed_count: int) -> bool:
        if removed_count <= 0:
            self.info('message count to removed error: %d' % removed_count)
            return False
        # 0. get message file path
        path = batch.get('path')
        if path is None:
            receiver = batch.get('ID')
            filename = batch.get('filename')
            if receiver and filename:
                # message directory
                directory = self.__directory(receiver)
                # message file path
                path = os.path.join(directory, filename)
        if not self.exists(path):
            self.info('message file not exists: %s' % path)
            return False
        # 1. remove all message(s)
        self.info('remove message file: %s' % path)
        self.remove(path)
        # 2. store the rest messages back
        messages = batch.get('messages')
        if messages is None:
            return False
        total_count = len(messages)
        if removed_count < total_count:
            # remove message(s) partially
            messages = messages[removed_count:]
            for msg in messages:
                # message data
                data = json.dumps(msg) + '\n'
                self.append_text(text=data, path=path)
            self.info('the rest messages(%d) write back into file: %s' % path)
        return True
