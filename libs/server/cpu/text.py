# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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
    Text Content Processor
    ~~~~~~~~~~~~~~~~~~~~~~

    Text commands
"""

import random
from typing import List, Dict

from dimples import ReliableMessage
from dimples import Content, TextContent
from dimples import BaseContentProcessor
from dimples.server import SessionCenter

from ...utils import Singleton, Logging


class TextContentProcessor(BaseContentProcessor, Logging):
    """
        Text Content Processor
        ~~~~~~~~~~~~~~~~~~~~~~

    """

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        text = content.text
        self.info(msg='received text message from %s: "%s"' % (r_msg.sender, text))
        if text is None or len(text) == 0:
            return []
        else:
            text = text.lower()
        # text commands
        if text == 'all users':
            return _all_users()
        if text == 'active users':
            return _active_users()
        if text == 'request handlers':
            return _request_handlers()
        # error
        return []


def _all_users() -> List[Content]:
    center = SessionCenter()
    all_users = center.all_users()
    text = '%d users\n' % len(all_users)
    text += '\n----\n'
    for user in all_users:
        text += '- %s\n' % user
    content = TextContent.create(text=text)
    content['format'] = 'markdown'
    return [content]


def _active_users() -> List[Content]:
    center = SessionCenter()
    all_users = center.all_users()
    text = 'Totally %d users\n' % len(all_users)
    text += '\n'
    text += '| ID | Sockets |\n'
    text += '|----|---------|\n'
    count = 0
    for user in all_users:
        active_sessions = center.active_sessions(identifier=user)
        if len(active_sessions) == 0:
            continue
        else:
            count += 1
        text += '| %s |' % user
        for sess in active_sessions:
            text += ' _%s_' % str(sess.remote_address)
        text += ' |\n'
    text += '\n'
    text += '%d active users.' % count
    content = TextContent.create(text=text)
    content['format'] = 'markdown'
    return [content]


def _request_handlers() -> List[Content]:
    marker = RequestHandlerMarker()
    all_tags = marker.all_tags()
    text = '%d handlers\n' % len(all_tags)
    text += '\n'
    text += '| Tag | Sockets |\n'
    text += '|-----|---------|\n'
    for tag in all_tags:
        client_address = all_tags.get(tag, None)
        text += '| %d | _%s_ |\n' % (tag, client_address)
    content = TextContent.create(text=text)
    content['format'] = 'markdown'
    return [content]


@Singleton
class RequestHandlerMarker:

    def __init__(self):
        super().__init__()
        self.__pool: Dict[int, str] = {}

    def all_tags(self) -> Dict[int, str]:
        return self.__pool.copy()

    def get_tag(self, client_address) -> int:
        tag = random.randint(2**30, 2**32 - 1)
        self.__pool[tag] = str(client_address)
        return tag

    def del_tag(self, tag: int):
        self.__pool.pop(tag, None)
