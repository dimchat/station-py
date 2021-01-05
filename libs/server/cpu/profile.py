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
    Profile Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimp import ForwardContent, Command, DocumentCommand

from dimsdk import CommandProcessor, DocumentCommandProcessor as SuperCommandProcessor

from ...common import Database
from ..messenger import ServerMessenger


class DocumentCommandProcessor(SuperCommandProcessor):

    def get_context(self, key: str):
        return self.messenger.get_context(key=key)

    @SuperCommandProcessor.messenger.getter
    def messenger(self) -> ServerMessenger:
        return super().messenger

    @property
    def database(self) -> Database:
        return self.get_context('database')

    def __check_login(self, cmd: DocumentCommand, sender: ID) -> bool:
        profile = cmd.document
        if profile is not None:
            # this command is submitting profile, not querying
            return False
        # respond login message when querying profile
        identifier = cmd.identifier
        msg = self.database.login_message(identifier=identifier)
        if msg is None:
            # login message not found
            return False
        cmd = ForwardContent(message=msg)
        assert isinstance(self.messenger, ServerMessenger), 'messenger error: %s' % self.messenger
        return self.messenger.send_content(sender=None, receiver=sender, content=cmd)

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, DocumentCommand), 'command error: %s' % cmd
        res = super().execute(cmd=cmd, msg=msg)
        self.__check_login(cmd=cmd, sender=msg.sender)
        return res


# register
dpu = DocumentCommandProcessor()
CommandProcessor.register(command=Command.PROFILE, cpu=dpu)
CommandProcessor.register(command=Command.DOCUMENT, cpu=dpu)
