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
    Receipt Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional

from dimp import ID
from dimp import InstantMessage
from dimp import Content
from dimp import Command
from dimsdk import ReceiptCommand
from dimsdk import CommandProcessor

from ..utils import Log


class ReceiptCommandProcessor(CommandProcessor):

    def __init__(self, messenger):
        super().__init__(messenger=messenger)

    @staticmethod
    def info(msg: str):
        Log.info('Receipt:\t%s' % msg)
        pass

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, ReceiptCommand), 'text content error: %s' % content
        nickname = self.facebook.nickname(identifier=sender)
        self.info('Received receipt message from %s: %s' % (nickname, content))
        return None


# register
CommandProcessor.register(command=Command.RECEIPT, processor_class=ReceiptCommandProcessor)
