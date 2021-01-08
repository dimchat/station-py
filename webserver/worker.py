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

"""
    Delegate for Web Server
    ~~~~~~~~~~~~~~~~~~~~~~~

"""

import json
from typing import Optional

from dimp import ID
from dimp import Content, TextContent
from dimsdk import Facebook

from libs.utils import Log

from webserver.config import msg_url
from webserver.database import UserTable, MessageTable


class Worker:

    def __init__(self, facebook: Facebook):
        super().__init__()
        self.facebook = facebook
        self.user_table = UserTable(facebook=facebook)
        self.msg_table = MessageTable(facebook=facebook)

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def identifier(self, identifier: str) -> Optional[ID]:
        try:
            return ID.parse(identifier=identifier)
        except ValueError:
            self.error('ID error: %s' % identifier)

    def user_info(self, identifier: ID) -> Optional[dict]:
        return self.user_table.user_info(identifier=identifier)

    def outlines(self) -> list:
        return self.user_table.users()

    def message(self, signature: str) -> Optional[dict]:
        msg = self.msg_table.load(signature=signature)
        if msg is None:
            Log.error('failed to load message: %s' % signature)
            return None
        # message content
        content = msg.get('content')
        if content is None:
            data = msg['data']
            content = Content.parse(content=json.loads(data))
            assert isinstance(content, TextContent), 'content error: %s' % data
            msg['content'] = content
        # message url
        link = msg.get('link')
        if link is None:
            link = msg_url(signature=signature)
            msg['link'] = link
        return msg.dictionary

    def messages(self, identifier: ID, start: int, count: int) -> list:
        array = []
        lines = self.user_table.messages(identifier=identifier, start=start, count=count)
        for l in lines:
            pair = l.split(',')
            signature = pair[0].strip()
            if len(signature) == 0:
                continue
            msg = self.message(signature=signature)
            if msg is not None:
                array.append(msg)
        return array
