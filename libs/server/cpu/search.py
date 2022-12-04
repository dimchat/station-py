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

from typing import List

from dimp import ID, Meta
from dimp import ReliableMessage
from dimp import Content

from dimples.server import SessionCenter

from dimples import BaseCommandProcessor
from dimples.common import CommonFacebook

from ...common import SearchCommand


def online_users(facebook, start: int, limit: int) -> (List[ID], dict):
    if start < 0:
        start = 0
    if limit < 0:
        limit = 1024
    pos = 0
    end = start + limit
    # check all users in session center
    center = SessionCenter()
    all_users = center.all_users()
    users = []
    results = {}
    for item in all_users:
        if not center.is_active(identifier=item):
            continue
        pos += 1
        if pos < start:
            continue
        elif pos >= end:
            break
        users.append(item)
        meta = facebook.meta(identifier=item)
        if isinstance(meta, Meta):
            results[str(item)] = meta.dictionary
    return list(users), results


# noinspection PyUnusedLocal
def save_response(facebook, station: ID, users: List[ID], results: dict) -> List[Content]:
    # TODO: Save online users in a text file
    return []


class SearchCommandProcessor(BaseCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, SearchCommand), 'search command error: %s' % content
        if content.users is not None or content.results is not None:
            # this is a response
            return save_response(self.facebook, station=msg.sender, users=content.users, results=content.results)
        # this is a request
        facebook = self.facebook
        keywords = content.keywords
        if keywords is None:
            text = 'Search command error.'
            return self._respond_text(text=text)
        elif keywords == SearchCommand.ONLINE_USERS:
            users, results = online_users(facebook, start=content.start, limit=content.limit)
        else:
            # let search bot (archivist) to do the job
            return []
        res = SearchCommand.respond(request=content, keywords=keywords, users=users, results=results)
        station = facebook.current_user
        res.station = station.identifier
        return [res]
