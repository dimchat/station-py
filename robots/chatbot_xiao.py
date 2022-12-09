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

import threading
from typing import Optional, Union

from dimples import ContentType
from dimples import ContentProcessor, ContentProcessorCreator
from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client import ChatTextContentProcessor
from libs.client import ClientProcessor, ClientContentProcessorCreator

from robots.shared import GlobalVariable
from robots.shared import chat_bots
from robots.shared import create_config, create_terminal


class BotTextContentProcessor(ChatTextContentProcessor):

    def __init__(self, facebook, messenger):
        shared = GlobalVariable()
        bots = chat_bots(names=['xiaoi'], shared=shared)  # chat bot
        super().__init__(facebook=facebook, messenger=messenger, bots=bots)


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return BotTextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


def main():
    config = create_config(app_name='ChatBot: Xiao I', default_config=DEFAULT_CONFIG)
    terminal = create_terminal(config=config, processor_class=BotMessageProcessor)
    thread = threading.Thread(target=terminal.run, daemon=False)
    thread.start()


if __name__ == '__main__':
    main()
