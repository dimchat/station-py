#! /usr/bin/env python3
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
    Chat bot: 'XiaoXiao'
    ~~~~~~~~~~~~~~~~~~~~

    Chat bot powered by XiaoI
"""

import sys
import os
from typing import Optional, List

from dimp import ID
from dimp import ContentType, Content, TextContent
from dimsdk import ContentProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import Storage
from libs.common import ChatTextContentProcessor
from libs.client import Terminal, ClientMessenger

from robots.nlp import chat_bots
from robots.config import g_station
from robots.config import dims_connect


def load_statistics(prefix: str) -> List[str]:
    results = []
    path = os.path.join(Storage.root, 'counter.txt')
    text = Storage.read_text(path=path)
    if text is not None:
        array = text.splitlines()
        for item in array:
            if item.startswith(prefix):
                results.append(item)
    return results


def stat_record(columns: List[str]) -> str:
    if len(columns) == 4:
        rec_time = columns[0]
        login_cnt = int(columns[1])
        msg_cnt = int(columns[2])
        g_msg_cnt = int(columns[3])
        return '[%s]\n' \
               '\t%d login record(s),\n' \
               '\t%d msg(s) sent,\n' \
               '\t(%d group msgs).\n' \
               % (rec_time, login_cnt, msg_cnt + g_msg_cnt, g_msg_cnt)
    return '\t'.join(columns)


#
#   Text Content Processor
#
class TextContentProcessor(ChatTextContentProcessor, Logging):

    def __stat(self, condition: str, group: Optional[ID]) -> Optional[TextContent]:
        results = load_statistics(prefix=condition.strip())
        count = len(results)
        self.info('got %d record(s) matched: %s' % (count, condition))
        if count > 32:
            results = results[-32:]
        if count > 0:
            text = 'Statistics:  "%s"\n\n' % condition
            for item in results:
                text += stat_record(columns=item.split('\t'))
        else:
            text = 'No record'
        res = TextContent(text=text)
        if group is not None:
            res.group = group
        return res

    def _query(self, content: Content, sender: ID) -> TextContent:
        assert isinstance(content, TextContent), 'content error: %s' % content
        text = content.text
        if text.startswith('stat') or text.startswith('Stat'):
            return self.__stat(condition=text[5:], group=content.group)
        return super()._query(content=content, sender=sender)


bots = chat_bots(names=['xiaoi'])  # chat bot
ContentProcessor.register(content_type=ContentType.TEXT, cpu=TextContentProcessor(bots=bots))


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_facebook = g_messenger.facebook


if __name__ == '__main__':

    # set current user
    bot_id = 'xiaoxiao@2PhVByg7PhEtYPNzW5ALk9ygf6wop1gTccp'  # chat bot XiaoI
    g_facebook.current_user = g_facebook.user(identifier=ID.parse(identifier=bot_id))

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, server=g_station)
