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
    Response Processor for search/online users
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. search users with keyword(s)
    2. show online users (connected)
"""

from typing import Optional

from dimp import json_encode
from dimp import ReliableMessage
from dimp import Content
from dimp import Command
from dimsdk import CommandProcessor

from libs.common import SearchCommand


class SearchCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        # message
        message = cmd.get('message')
        print('search response: %s' % message)
        # users
        users = cmd.get('users')
        if users is not None:
            print('      users:', json_encode(users))
        # results
        results = cmd.get('results')
        if results is not None:
            print('      results:', json_encode(results))
        return None


class UsersCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        # message
        message = cmd.get('message')
        print('online users response: %s' % message)
        # users
        users = cmd.get('users')
        if users is not None:
            print('      users:', json_encode(users))
        return None


# register
CommandProcessor.register(command=SearchCommand.SEARCH, cpu=SearchCommandProcessor())
CommandProcessor.register(command=SearchCommand.ONLINE_USERS, cpu=UsersCommandProcessor())
