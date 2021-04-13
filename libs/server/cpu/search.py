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

from dimp import ID, Meta
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import CommandProcessor

from ...utils import NotificationCenter
from ...common import NotificationNames
from ...common import SearchCommand
from ...common import Database

from ..session import SessionServer


g_session_server = SessionServer()
g_database = Database()


class SearchCommandProcessor(CommandProcessor):

    @staticmethod
    def __search(cmd: SearchCommand) -> Optional[Content]:
        # keywords
        keywords = cmd.get('keywords')
        if keywords is None:
            return TextContent(text='Search command error')
        keywords = keywords.split(' ')
        start = cmd.start
        limit = cmd.limit
        # search in database
        results = g_database.search(keywords=keywords, start=start, limit=limit)
        users = list(results.keys())
        return _new_search_command(cmd=cmd, users=users, results=results)

    def __process(self, cmd: SearchCommand) -> Optional[Content]:
        # save meta for users
        _save_metas(cmd=cmd, facebook=self.facebook)
        # TODO: show users?
        return None

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        users = cmd.users
        if users is None:
            return self.__search(cmd=cmd)
        else:
            return self.__process(cmd=cmd)


def _new_search_command(cmd: SearchCommand, users: list, results: dict) -> SearchCommand:
    info = cmd.copy_dictionary(False)
    info.pop('sn', None)
    info.pop('time', None)
    cmd = SearchCommand(cmd=info)
    cmd.users = users
    cmd.results = results
    return cmd


def _save_metas(cmd: SearchCommand, facebook):
    results = cmd.results
    for key, value in results.items():
        identifier = ID.parse(identifier=key)
        meta = Meta.parse(meta=value)
        if identifier is not None and meta is not None:
            # assert meta.match_identifier(identifier=identifier), 'meta error'
            facebook.save_meta(meta=meta, identifier=identifier)


class UsersCommandProcessor(CommandProcessor):

    def __search(self, cmd: SearchCommand) -> Optional[Content]:
        facebook = self.facebook
        start = cmd.start
        limit = cmd.limit
        # get active users
        users = g_session_server.active_users(start=start, limit=limit)
        results = {}
        for item in users:
            meta = facebook.meta(identifier=item)
            if isinstance(meta, Meta):
                results[str(item)] = meta.dictionary
        return _new_search_command(cmd=cmd, users=list(users), results=results)

    def __process(self, cmd: SearchCommand) -> Optional[Content]:
        # save meta for users
        _save_metas(cmd=cmd, facebook=self.facebook)
        # post roamers
        nc = NotificationCenter()
        users = cmd.users
        for item in users:
            # post notification: USER_ROAMING
            nc.post(name=NotificationNames.USER_ROAMING, sender=self, info={
                'ID': item
            })
        return None

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        users = cmd.users
        if users is None:
            return self.__search(cmd=cmd)
        else:
            return self.__process(cmd=cmd)


# register
spu = SearchCommandProcessor()
CommandProcessor.register(command=SearchCommand.SEARCH, cpu=SearchCommandProcessor())
CommandProcessor.register(command=SearchCommand.ONLINE_USERS, cpu=UsersCommandProcessor())
