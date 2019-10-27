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

from dimp import ID
from dimp import Content
from dimp import Command

from libs.common import ReceiptCommand
from libs.server import Session

from .cpu import CPU, processor_classes


class ReportCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        if type(self) != ReportCommandProcessor:
            raise AssertionError('override me!')
        self.info('client broadcast %s, %s' % (sender, cmd))
        title = cmd.get('title')
        # get processor from cache
        cpu = self.processors.get(title)
        if cpu is None:
            # try to create new processor
            clazz = processor_classes.get(title)
            if clazz is not None:
                cpu = self.create_cpu(clazz)
                self.processors[title] = cpu
        elif cpu is self:
            # NOTICE: dead cycle!
            cpu = None
        if cpu is not None:
            # process by subclass
            return cpu.process(cmd=cmd, sender=sender)
        if 'report' == title:
            # compatible with v1.0
            state = cmd.get('state')
            self.info('client report state %s' % state)
            if state is not None:
                session = self.request_handler.current_session(identifier=sender)
                if 'background' == state:
                    session.active = False
                elif 'foreground' == state:
                    # welcome back!
                    self.receptionist.add_guest(identifier=session.identifier)
                    session.active = True
                else:
                    self.error('unknown state %s' % state)
                    session.active = True
                return ReceiptCommand.receipt(message='Client state received')
        self.error('command not supported yet: %s' % cmd)


class APNsCommandProcessor(ReportCommandProcessor):

    def process(self, cmd: Command, sender: ID) -> Content:
        # submit device token for APNs
        token = cmd.get('device_token')
        self.info('client report token %s' % token)
        if token is not None:
            self.database.save_device_token(token=token, identifier=sender)
            return ReceiptCommand.receipt(message='Token received')


class OnlineCommandProcessor(ReportCommandProcessor):

    def process(self, cmd: Command, sender: ID) -> Content:
        # welcome back!
        self.info('client online')
        self.receptionist.add_guest(identifier=sender)
        session = self.request_handler.current_session(identifier=sender)
        if isinstance(session, Session):
            session.active = True
        return ReceiptCommand.receipt(message='Client online received')


class OfflineCommandProcessor(ReportCommandProcessor):

    def process(self, cmd: Command, sender: ID) -> Content:
        # goodbye!
        self.info('client offline')
        session = self.request_handler.current_session(identifier=sender)
        if isinstance(session, Session):
            session.active = False
        return ReceiptCommand.receipt(message='Client offline received')


# register
processor_classes['apns'] = APNsCommandProcessor
processor_classes['online'] = OnlineCommandProcessor
processor_classes['offline'] = OfflineCommandProcessor
