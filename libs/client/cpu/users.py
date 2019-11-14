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
    Command Processor for 'users'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    show online users (connected)
"""

import json
from typing import Optional

from dimp import ID
from dimp import InstantMessage
from dimp import Content
from dimp import Command
from dimsdk import CommandProcessor


class UsersCommandProcessor(CommandProcessor):

    @property
    def session_server(self):  # SessionServer
        return self.get_context('session_server')

    def __random_users(self, max_count=20) -> Optional[Content]:
        pass

    @staticmethod
    def __update(content: Content) -> Optional[Content]:
        if 'users' in content:
            users = content['users']
            print('      users:', json.dumps(users))
        return None

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, Command), 'command error: %s' % content
        # message
        message = content.get('message')
        if message is None:
            return self.__random_users()
        else:
            return self.__update(content=content)


# register
CommandProcessor.register(command='users', processor_class=UsersCommandProcessor)
