# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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

"""
    Database module
    ~~~~~~~~~~~~~~~

"""

import json
import os
from typing import Optional

from dimp import ID, ANYONE
from dimp import ReliableMessage
from dimsdk import Facebook

from libs.common import Storage

from webserver.config import usr_path, msg_path, usr_url


class UserTable(Storage):

    def __init__(self, facebook: Facebook):
        super().__init__()
        self.facebook = facebook

    def __recommended_users(self, address: str) -> list:
        path = usr_path(address=address)
        path = os.path.join(path, 'users.txt')
        text = self.read_text(path=path)
        if text is None:
            return []
        else:
            return text.splitlines()

    def users(self) -> list:
        array = []
        anyone = ANYONE
        id_list = self.__recommended_users(address=anyone.address)
        for item in id_list:
            identifier = item.strip()
            if len(identifier) == 0:
                # skip empty lines
                continue
            identifier = ID.parse(identifier=identifier)
            info = self.user_info(identifier=identifier)
            if info is None:
                # user info not found
                continue
            array.append(info)
        return array

    def user_info(self, identifier: ID) -> Optional[dict]:
        doc = self.facebook.document(identifier=identifier)
        name = doc.name
        url = usr_url(identifier=identifier)
        desc = json.dumps(doc.dictionary)
        return {
            'ID': identifier,
            'name': name,
            'link': url,
            'desc': desc,
        }

    def __load_messages(self, address: str) -> list:
        path = usr_path(address=address)
        path = os.path.join(path, 'messages.txt')
        text = self.read_text(path=path)
        if text is None:
            return []
        else:
            return text.splitlines()

    def messages(self, identifier: ID, start: int, count: int) -> list:
        array = []
        address = str(identifier.address)
        lines = self.__load_messages(address=address)
        start = len(lines) - start - 1
        stop = max(start - count, -1)
        for index in range(start, stop, -1):
            msg = lines[index].strip()
            if len(msg) == 0:
                # skip empty lines
                continue
            array.append(msg)
        return array


class MessageTable(Storage):

    def __init__(self, facebook: Facebook):
        super().__init__()
        self.facebook = facebook

    def __load_message(self, signature: str) -> Optional[ReliableMessage]:
        path = msg_path(signature=signature)
        msg = self.read_json(path=path)
        if msg is not None:
            return ReliableMessage(msg)

    def load(self, signature: str) -> Optional[ReliableMessage]:
        return self.__load_message(signature=signature)

    def save(self, msg: ReliableMessage) -> bool:
        signature = msg['signature']
        timestamp = msg.time
        path = msg_path(signature=signature)
        if not self.write_json(container=msg, path=path):
            return False
        # append msg info to user's messages list
        sender = msg.sender
        path = usr_path(address=sender.address)
        path = os.path.join(path, 'messages.txt')
        text = '%s,%d\n' % (signature, timestamp)
        return self.append_text(text=text, path=path)
