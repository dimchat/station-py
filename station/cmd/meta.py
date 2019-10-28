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
    Command Processor for 'meta'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    meta protocol
"""

from dimp import ID
from dimp import Content, TextContent
from dimp import Command, MetaCommand

from libs.common import ReceiptCommand

from .cpu import CPU


class MetaCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        assert isinstance(cmd, MetaCommand)
        identifier = self.facebook.identifier(cmd.identifier)
        meta = cmd.meta
        if meta is not None:
            # received a meta for ID
            self.info('received meta %s' % identifier)
            if self.facebook.save_meta(identifier=identifier, meta=meta):
                self.info('meta saved %s, %s' % (identifier, meta))
                return ReceiptCommand.new(message='Meta for %s received!' % identifier)
            else:
                self.error('meta not match %s, %s' % (identifier, meta))
                return TextContent.new(text='Meta not match %s!' % identifier)
        # querying meta for ID
        self.info('search meta %s' % identifier)
        meta = self.facebook.meta(identifier=identifier)
        # response
        if meta is not None:
            return MetaCommand.response(identifier=identifier, meta=meta)
        else:
            return TextContent.new(text='Sorry, meta for %s not found.' % identifier)
