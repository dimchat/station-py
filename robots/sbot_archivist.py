#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Station bot: 'Archivist'
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Bot as Search Engine to managing metas & documents
"""

import threading
from typing import Optional, Union

from dimples import ContentType
from dimples import ContentProcessor, ContentProcessorCreator
from dimples.client import ClientProcessor, ClientContentProcessorCreator
from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client.protocol import SearchCommand
from libs.client.cpu import SearchCommandProcessor
from robots.shared import create_config, create_terminal
from robots.shared import check_bot_id


class ArchivistContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd_name: str) -> Optional[ContentProcessor]:
        # search
        if cmd_name == SearchCommand.SEARCH:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == SearchCommand.ONLINE_USERS:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd_name=cmd_name)


class ArchivistMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ArchivistContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


def main():
    config = create_config(app_name='DIM Search Engine', default_config=DEFAULT_CONFIG)
    if not check_bot_id(config=config, ans_name='archivist'):
        raise LookupError('Failed to get Bot ID: %s' % config)
    terminal = create_terminal(config=config, processor_class=ArchivistMessageProcessor)
    thread = threading.Thread(target=terminal.run, daemon=False)
    thread.start()


if __name__ == '__main__':
    main()
