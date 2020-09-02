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
from dimp import ForwardContent, Command, ProfileCommand

from dimsdk import CommandProcessor
from dimsdk import ProfileCommandProcessor as SuperCommandProcessor

from ...common import Database


class ProfileCommandProcessor(SuperCommandProcessor):

    @property
    def database(self) -> Database:
        return self.get_context('database')

    def __check_login(self, cmd: ProfileCommand, sender: ID) -> bool:
        profile = cmd.profile
        if profile is not None:
            # this command is submitting profile, not querying
            return False
        # respond login message when querying profile
        identifier = cmd.identifier
        msg = self.database.login_message(identifier=identifier)
        if msg is None:
            # login message not found
            return False
        cmd = ForwardContent.new(message=msg)
        return self.messenger.send_content(content=cmd, receiver=sender)

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(content, ProfileCommand), 'command error: %s' % content
        res = super().process(content=content, sender=sender, msg=msg)
        self.__check_login(cmd=content, sender=sender)
        return res


# register
CommandProcessor.register(command=Command.PROFILE, processor_class=ProfileCommandProcessor)
