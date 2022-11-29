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
    Command Processor for 'report'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Report protocol
"""

from typing import List

from dimsdk import ReliableMessage
from dimsdk import Content

from dimples.server.cpu import ReportCommandProcessor as SuperCommandProcessor

from ...utils import Logging
from ...database import Database
from ...common import ReportCommand


g_database = Database()


class ReportCommandProcessor(SuperCommandProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'report command error: %s' % content
        # report title
        title = content.title
        if title == 'apns':
            return self.__process_apns(content=content, msg=msg)
        else:
            return super().process(content=content, msg=msg)

    def __process_apns(self, content: ReportCommand, msg: ReliableMessage) -> List[Content]:
        # submit device token for APNs
        token = content.get('device_token')
        if token is None or len(token) == 0:
            return []
        g_database.save_device_token(token=token, identifier=msg.sender)
        text = 'Token received.'
        return self._respond_text(text=text)
