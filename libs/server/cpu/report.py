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

from dimp import ReliableMessage
from dimp import Content, Command
from dimsdk import CommandProcessor

from ...utils import Logging
from ...utils import NotificationCenter
from ...database import Database
from ...common import NotificationNames
from ...common import ReportCommand
from ...common import CommonFacebook

from ..session import Session


g_database = Database()


class ReportCommandProcessor(CommandProcessor, Logging):

    def processor_for_name(self, name: str) -> Optional[CommandProcessor]:
        messenger = self.messenger
        # from ..messenger import ServerMessenger
        # assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
        processor = messenger.processor
        # from ..processor import ServerProcessor
        # assert isinstance(processor, ServerProcessor), 'message processor error: %s' % processor
        return processor.get_processor_by_name(cmd_name=name)

    def _post_notification(self, cmd: Command, session: Session):
        if session.active:
            notification = NotificationNames.USER_ONLINE
        else:
            notification = NotificationNames.USER_OFFLINE
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error'
        station = facebook.current_user
        sid = station.identifier
        # post notification
        NotificationCenter().post(name=notification, sender=self, info={
            'ID': str(session.identifier),
            'client_address': session.client_address,
            'station': str(sid),
            'time': cmd.time,
        })

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
            active = False
        else:  # 'foreground'
            # save as 'online'
            if not g_database.save_online(cmd=cmd, msg=msg):
                self.error('online command error/expired: %s' % cmd)
                return []
            active = True
        messenger = self.messenger
        # from ..messenger import ServerMessenger
        # assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
        session = messenger.session
        if session is not None:
            assert session.identifier == msg.sender, 'session ID not match: %s, %s' % (msg.sender, session)
            session.active = active
            self._post_notification(cmd=cmd, session=session)
        text = 'Client state received.'
        return self._respond_receipt(text=text)

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, ReportCommand), 'report command error: %s' % cmd
        # report title
        title = cmd.title
        if title == ReportCommand.REPORT:
            return self.__process_old_report(cmd=cmd, msg=msg)
        # get CPU by report title
        cpu = self.processor_for_name(name=title)
        # check and run
        if cpu is None:
            text = 'Report command (title: %s) not support yet!' % title
            return self._respond_text(text=text)
        elif cpu is self:
            raise AssertionError('Dead cycle! report cmd: %s' % cmd)
        # assert isinstance(cpu, CommandProcessor), 'CPU error: %s' % cpu
        return cpu.execute(cmd=cmd, msg=msg)


class APNsCommandProcessor(ReportCommandProcessor):

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, Command), 'command error: %s' % cmd
        # submit device token for APNs
        token = cmd.get('device_token')
        if token is None or len(token) == 0:
            return []
        g_database.save_device_token(token=token, identifier=msg.sender)
        text = 'Token received.'
        return self._respond_receipt(text=text)


class OnlineCommandProcessor(ReportCommandProcessor):

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, ReportCommand), 'online report command error: %s' % cmd
        # save 'online'
        if not g_database.save_online(cmd=cmd, msg=msg):
            self.error('online command error/expired: %s' % cmd)
            return []
        # welcome back!
        messenger = self.messenger
        # from ..messenger import ServerMessenger
        # assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
        session = messenger.session
        if session is not None:
            session.active = True
            self._post_notification(cmd=cmd, session=session)
            # TODO: notification for pushing offline message(s) from 'last_time'
        text = 'Client online received.'
        return self._respond_receipt(text=text)


class OfflineCommandProcessor(ReportCommandProcessor):

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, ReportCommand), 'offline report command error: %s' % cmd
        # save 'offline'
        if not g_database.save_offline(cmd=cmd, msg=msg):
            self.error('online command error/expired: %s' % cmd)
            return []
        # goodbye!
        messenger = self.messenger
        # from ..messenger import ServerMessenger
        # assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
        session = messenger.session
        if session is not None:
            session.active = False
            self._post_notification(cmd=cmd, session=session)
        text = 'Client offline received.'
        return self._respond_receipt(text=text)
