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
    Text Content Processor
    ~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional

from dimp import ID
from dimp import InstantMessage
from dimp import ContentType, Content, TextContent
from dimsdk import ContentProcessor
from dimsdk import Dialog


class TextContentProcessor(ContentProcessor):

    def __init__(self, context: dict):
        super().__init__(context=context)
        self.__dialog: Dialog = None

    @property
    def bots(self) -> list:
        array = self.context.get('bots')
        if array is None:
            array = []
            self.context['bots'] = array
        return array

    @property
    def dialog(self) -> Dialog:
        if self.__dialog is None:
            d = Dialog()
            d.bots = self.bots
            self.__dialog = d
        return self.__dialog

    @property
    def remote_address(self):  # (IP, port)
        return self.context.get('remote_address')

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        self.info('@@@ call NLP and response to the client %s, %s' % (self.remote_address, sender))
        nickname = self.facebook.nickname(identifier=sender)
        response = self.dialog.query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            assert isinstance(content, TextContent)
            question = content.text
            answer = response.text
            self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            return response
        # TEST: response client with the same message here
        self.info('Dialog > message from %s(%s): %s' % (nickname, sender, content))
        return content


# register
ContentProcessor.register(content_type=ContentType.Text, processor_class=TextContentProcessor)
