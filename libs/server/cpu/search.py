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
    Command Processor for search/online users
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. search users with keyword(s)
    2. show online users (connected)
"""

from typing import Optional

from dimp import ID
from dimp import InstantMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import CommandProcessor

from ...common import SearchCommand
from ...common import Database
from ..session import SessionServer


class SearchCommandProcessor(CommandProcessor):

    @property
    def database(self) -> Database:
        return self.get_context('database')

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, Command), 'command error: %s' % content
        # keywords
        keywords = content.get('keywords')
        if keywords is None:
            return TextContent.new(text='Search command error')
        keywords = keywords.split(' ')
        # search in database
        results = self.database.search(keywords=keywords)
        users = list(results.keys())
        return SearchCommand.new(users=users, results=results)


class UsersCommandProcessor(CommandProcessor):

    @property
    def session_server(self) -> SessionServer:
        return self.get_context('session_server')

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Optional[Content]:
        assert isinstance(content, Command), 'command error: %s' % content
        facebook = self.facebook
        users = self.session_server.random_users()
        results = {}
        for item in users:
            meta = facebook.meta(identifier=item)
            if meta is not None:
                results[item] = meta
        return SearchCommand.new(users=users, results=results)


# register
CommandProcessor.register(command='search', processor_class=SearchCommandProcessor)
CommandProcessor.register(command='users', processor_class=UsersCommandProcessor)
