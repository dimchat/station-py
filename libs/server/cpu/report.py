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

from typing import List, Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content, Command
from dimsdk import Station
from dimsdk import ContentProcessor
from dimsdk.cpu import BaseCommandProcessor

from ...utils import Logging
from ...utils import NotificationCenter
from ...database import Database
from ...common import NotificationNames
from ...common import ReportCommand
from ...common import CommonFacebook

from ..session import Session


g_database = Database()


class ReportCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def current_station(self) -> Station:
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        current = facebook.current_user
        assert isinstance(current, Station), 'current station error: %s' % current
        return current

    @property
    def current_session(self) -> Session:
        messenger = self.messenger
        from ..messenger import ServerMessenger
        if isinstance(messenger, ServerMessenger):
            return messenger.session

    def processor_for_name(self, name: str) -> Optional[ContentProcessor]:
        messenger = self.messenger
        processor = messenger.processor
        from ..processor import ServerProcessor
        assert isinstance(processor, ServerProcessor), 'message processor error: %s' % processor
        return processor.get_processor_by_name(cmd_name=name)

    def __process_old_report(self, cmd: ReportCommand, msg: ReliableMessage) -> List[Content]:
        # compatible with v1.0
        state = cmd.get('state')
        if state is None:
            # command error
            return []
        elif 'background' == state:
            # save as 'offline'
            if not g_database.save_offline(cmd=cmd, msg=msg):
                self.error('offline command error/expired: %s' % cmd)
                return []
            post_from_rcp(cpu=self, online=False, cmd=cmd, sender=msg.sender)
        else:  # 'foreground'
            # save as 'online'
            if not g_database.save_online(cmd=cmd, msg=msg):
                self.error('online command error/expired: %s' % cmd)
                return []
            post_from_rcp(cpu=self, online=True, cmd=cmd, sender=msg.sender)
        text = 'Client state received.'
        return self._respond_receipt(text=text)

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'report command error: %s' % content
        # report title
        title = content.title
        if title == ReportCommand.REPORT:
            return self.__process_old_report(cmd=content, msg=msg)
        # get CPU by report title
        cpu = self.processor_for_name(name=title)
        # check and run
        if cpu is None:
            text = 'Report command (title: %s) not support yet!' % title
            return self._respond_text(text=text)
        elif cpu is self:
            raise AssertionError('Dead cycle! report cmd: %s' % content)
        # assert isinstance(cpu, CommandProcessor), 'CPU error: %s' % cpu
        return cpu.process(content=content, msg=msg)


class APNsCommandProcessor(ReportCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, Command), 'command error: %s' % content
        # submit device token for APNs
        token = content.get('device_token')
        if token is None or len(token) == 0:
            return []
        g_database.save_device_token(token=token, identifier=msg.sender)
        text = 'Token received.'
        return self._respond_receipt(text=text)


class OnlineCommandProcessor(ReportCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'online report command error: %s' % content
        # save 'online'
        if not g_database.save_online(cmd=content, msg=msg):
            self.error('online command error/expired: %s' % content)
            return []
        # welcome back!
        post_from_rcp(cpu=self, online=True, cmd=content, sender=msg.sender)
        # TODO: notification for pushing offline message(s) from 'last_time'
        text = 'Client online received.'
        return self._respond_receipt(text=text)


class OfflineCommandProcessor(ReportCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'offline report command error: %s' % content
        # save 'offline'
        if not g_database.save_offline(cmd=content, msg=msg):
            self.error('online command error/expired: %s' % content)
            return []
        # goodbye!
        post_from_rcp(cpu=self, online=False, cmd=content, sender=msg.sender)
        text = 'Client offline received.'
        return self._respond_receipt(text=text)


def post_from_rcp(cpu: ReportCommandProcessor, online: bool, cmd: Command, sender: ID):
    if online:
        notification = NotificationNames.USER_ONLINE
    else:
        notification = NotificationNames.USER_OFFLINE
    # check session
    session = cpu.current_session
    if session is not None and session.identifier == sender:
        # login this station
        session.active = online
        NotificationCenter().post(name=notification, sender=cpu, info={
            'ID': str(sender),
            'client_address': session.client_address,
            'station': str(cpu.current_station.identifier),
            'time': cmd.time,
        })
    else:
        # login other station
        NotificationCenter().post(name=notification, sender=cpu, info={
            'ID': str(sender),
            'time': cmd.time,
        })
