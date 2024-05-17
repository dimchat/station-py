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

from typing import Optional, Union

from dimples import ContentType
from dimples import ContentProcessor, ContentProcessorCreator
from dimples.client import ClientContentProcessorCreator
from dimples.utils import Log, Runner
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client.protocol import SearchCommand, StorageCommand
from libs.client.cpu import SearchCommandProcessor, StorageCommandProcessor
from libs.client import ClientProcessor

from sbots.shared import start_bot


class ArchivistContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # search
        if cmd == SearchCommand.SEARCH:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == SearchCommand.ONLINE_USERS:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # storage
        if cmd == StorageCommand.STORAGE:
            return StorageCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == StorageCommand.CONTACTS or cmd == StorageCommand.PRIVATE_KEY:
            return StorageCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)


class ArchivistMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ArchivistContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


async def main():
    client = await start_bot(default_config=DEFAULT_CONFIG,
                             app_name='DIM Search Engine',
                             ans_name='archivist',
                             processor_class=ArchivistMessageProcessor)
    # main run loop
    await client.start()
    await client.run()
    # await client.stop()
    Log.warning(msg='bot stopped: %s' % client)


if __name__ == '__main__':
    Runner.sync_run(main=main())
