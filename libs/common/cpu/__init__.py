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
    Command Processing Unites
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Processors for commands
"""

from dimp import ContentType, Command
from dimsdk import MuteCommand, BlockCommand
from dimsdk import ContentProcessor, CommandProcessor

from .file import FileContentProcessor

from .receipt import ReceiptCommandProcessor
from .mute import MuteCommandProcessor
from .block import BlockCommandProcessor
from .storage import StorageCommandProcessor


def register_content_processors():
    # files
    fpu = FileContentProcessor()
    ContentProcessor.register(content_type=ContentType.FILE, cpu=fpu)
    ContentProcessor.register(content_type=ContentType.IMAGE, cpu=fpu)
    ContentProcessor.register(content_type=ContentType.AUDIO, cpu=fpu)
    ContentProcessor.register(content_type=ContentType.VIDEO, cpu=fpu)
    # register
    CommandProcessor.register(command=Command.RECEIPT, cpu=ReceiptCommandProcessor())
    CommandProcessor.register(command=MuteCommand.MUTE, cpu=MuteCommandProcessor())
    CommandProcessor.register(command=BlockCommand.BLOCK, cpu=BlockCommandProcessor())
    pass


register_content_processors()


__all__ = [

    'FileContentProcessor',

    'ReceiptCommandProcessor',
    'MuteCommandProcessor',
    'BlockCommandProcessor',
    'StorageCommandProcessor',
]
