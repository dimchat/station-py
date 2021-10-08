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
    Command Processor for online users
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, List

from dimp import ID, Meta
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import CommandProcessor

from ...database import Database
from ...common import SearchCommand

from ..session import SessionServer


g_session_server = SessionServer()
g_database = Database()


def online_users(facebook, start: int, limit: int) -> (List[ID], dict):
    users = g_session_server.active_users(start=start, limit=limit)
    results = {}
    if limit > 0:
        # get meta when limit is set
        for item in users:
            meta = facebook.meta(identifier=item)
            if isinstance(meta, Meta):
                results[str(item)] = meta.dictionary
    return list(users), results


# noinspection PyUnusedLocal
def save_response(facebook, station: ID, users: List[ID], results: dict) -> Optional[Content]:
    # TODO: Save online users in a text file
    pass


class SearchCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        if cmd.users is not None or cmd.results is not None:
            # this is a response
            return save_response(self.facebook, station=msg.sender, users=cmd.users, results=cmd.results)
        # this is a request
        facebook = self.facebook
        keywords = cmd.keywords
        if keywords is None:
            return TextContent(text='Search command error')
        elif keywords == SearchCommand.ONLINE_USERS:
            users, results = online_users(facebook, start=cmd.start, limit=cmd.limit)
        else:
            # let search bot (archivist) to do the job
            return None
        res = SearchCommand.respond(request=cmd, keywords=keywords, users=users, results=results)
        station = facebook.current_user
        res.station = station.identifier
        return res


# register
spu = SearchCommandProcessor()
CommandProcessor.register(command=SearchCommand.SEARCH, cpu=spu)
CommandProcessor.register(command=SearchCommand.ONLINE_USERS, cpu=spu)
