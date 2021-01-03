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

from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import ReceiptCommand
from dimsdk import CommandProcessor

from ...common import ReportCommand
from ...common import Database
from ..session import Session


class ReportCommandProcessor(CommandProcessor):

    def get_context(self, key: str):
        return self.messenger.get_context(key=key)

    @property
    def database(self) -> Database:
        return self.get_context('database')

    @property
    def receptionist(self):
        return self.get_context('receptionist')

    def __process_old_report(self, cmd: ReportCommand, sender: ID) -> Optional[Content]:
        # compatible with v1.0
        state = cmd.get('state')
        if state is not None:
            session = self.messenger.current_session(identifier=sender)
            if 'background' == state:
                session.active = False
            elif 'foreground' == state:
                # welcome back!
                self.receptionist.add_guest(identifier=session.identifier)
                session.active = True
            else:
                session.active = True
            return ReceiptCommand(message='Client state received')

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, ReportCommand), 'report command error: %s' % cmd
        # report title
        title = cmd.title
        if title == ReportCommand.REPORT:
            return self.__process_old_report(cmd=cmd, sender=msg.sender)
        # get CPU by report title
        cpu = self.processor_for_name(command=title)
        # check and run
        if cpu is None:
            return TextContent(text='Report command (title: %s) not support yet!' % title)
        elif cpu is self:
            raise AssertionError('Dead cycle! report cmd: %s' % cmd)
        assert isinstance(cpu, CommandProcessor), 'CPU error: %s' % cpu
        cpu.messenger = self.messenger
        return cpu.execute(cmd=cmd, msg=msg)


class APNsCommandProcessor(ReportCommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, Command), 'command error: %s' % cmd
        # submit device token for APNs
        token = cmd.get('device_token')
        if token is not None:
            self.database.save_device_token(token=token, identifier=msg.sender)
            return ReceiptCommand(message='Token received')


class OnlineCommandProcessor(ReportCommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, ReportCommand), 'online report command error: %s' % cmd
        # welcome back!
        self.receptionist.add_guest(identifier=msg.sender)
        session = self.messenger.current_session(identifier=msg.sender)
        if isinstance(session, Session):
            session.active = True
        # TODO: notification for pushing offline message(s) from 'last_time'
        return ReceiptCommand(message='Client online received')


class OfflineCommandProcessor(ReportCommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, ReportCommand), 'offline report command error: %s' % cmd
        # goodbye!
        session = self.messenger.current_session(identifier=msg.sender)
        if isinstance(session, Session):
            session.active = False
        return ReceiptCommand(message='Client offline received')


# register
rpu = ReportCommandProcessor()
CommandProcessor.register(command=ReportCommand.REPORT, cpu=rpu)
CommandProcessor.register(command='broadcast', cpu=rpu)

CommandProcessor.register(command='apns', cpu=APNsCommandProcessor())
CommandProcessor.register(command=ReportCommand.ONLINE, cpu=OnlineCommandProcessor())
CommandProcessor.register(command=ReportCommand.OFFLINE, cpu=OfflineCommandProcessor())
