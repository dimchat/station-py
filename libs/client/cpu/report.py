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

from typing import List, Dict

from dimples import ReliableMessage
from dimples import Content, ReportCommand
from dimples import BaseCommandProcessor

from ...utils import Logging

from ...common.compatible import fix_report_command
from ...database import DeviceInfo
from ...database import Database
from ...common import CommonFacebook


class ReportCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def database(self) -> Database:
        db = self.facebook.database
        assert isinstance(db, Database), 'database error: %s' % db
        return db

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'report command error: %s' % content
        # compatible with v1.0
        fix_report_command(content=content)
        # report title
        title = content.title
        if title == 'apns':
            return self.__process_apns(content=content, msg=msg)
        else:
            return super().process(content=content, msg=msg)

    def __process_apns(self, content: ReportCommand, msg: ReliableMessage) -> List[Content]:
        # submit device token for APNs
        info = content.dictionary
        token = info.get('device_token')
        if token is None:
            token = info.get('token')
            if token is None:
                # token not found, try to get device
                info = info.get('device')
                if isinstance(info, Dict):
                    # device info found
                    token = info.get('token')
                else:
                    self.error(msg='device info not found: %s' % self)
                    return []
        if token is None or len(token) == 0:
            return []
        sender = msg.sender
        device = DeviceInfo.from_json(info=info)
        assert device is not None, 'failed to parse device info: %s' % info
        db = self.database
        db.add_device(device=device, identifier=sender)
        return self._respond_receipt(text='Device token received.', msg=msg, extra={
            'template': 'Device token received: ${ID}.',
            'replacements': {
                'ID': str(sender),
            }
        })
