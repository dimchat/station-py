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

import time
from typing import List, Tuple

from dimples import ID, Meta
from dimples import ReliableMessage
from dimples import Content

from dimples import BaseCommandProcessor
from dimples.common import CommonFacebook
from dimples.utils import CacheManager

from ...utils import Logging
from ...database import Database
from ...database.t_active import ActiveTable
from ..protocol import SearchCommand


class SearchCommandProcessor(BaseCommandProcessor, Logging):

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
            return self._respond_receipt(text='Search command error.', msg=msg)
        elif keywords == SearchCommand.ONLINE_USERS:
            users, results = online_users(facebook, start=content.start, limit=content.limit)
            self.info('Got %d recent online user(s)' % len(results))
        else:
            db = facebook.database
            assert isinstance(db, Database), 'database error: %s' % db
            users, results = search_users(keywords=keywords, start=content.start, limit=content.limit,
                                          database=db, facebook=facebook)
            self.info('Got %d account(s) matched %s' % (len(results), keywords))
        res = SearchCommand.respond(request=content, keywords=keywords, users=users, results=results)
        station = facebook.current_user
        res.station = station.identifier
        return [res]


#
#   Caches
#
ActiveTable.CACHE_REFRESHING = 2
ActiveTable.CACHE_EXPIRES = 8

g_search_cache = CacheManager().get_pool(name='search')


def online_users(facebook: CommonFacebook, start: int, limit: int) -> (List[ID], dict):
    if start < 0:
        start = 0
    if limit < 0:
        limit = 1024
    pos = 0
    end = start + limit
    # check all users in session center
    db = facebook.database
    assert isinstance(db, Database), 'database error: %s' % db
    active_users = db.active_users()
    users = []
    results = {}
    for item in active_users:
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


def search_users(keywords: str, start: int, limit: int,
                 database: Database, facebook: CommonFacebook) -> Tuple[List[ID], dict]:
    # 0. split keywords
    if keywords is None:
        kw_array = []
    else:
        kw_array = keywords.split(' ')
    assert start >= 0, 'start position error: %d' % start
    if limit > 0:
        end = start + limit
    else:
        # this is a request from another search bot in neighbor station,
        # only return ID list for it.
        end = start + 10240
    # 1. get from cache
    now = time.time()
    value, holder = g_search_cache.fetch(key=(keywords, start, end), now=now)
    if value is not None:
        # got it
        return value
    elif holder is not None:
        # search result expired, wait to reload
        holder.renewal(duration=8, now=now)
    # 2. do searching
    index = -1
    users: List[ID] = []
    results = {}
    all_documents = database.scan_documents()
    for doc in all_documents:
        # get user info
        identifier = doc.identifier
        name = doc.name
        if name is None:
            info = str(identifier)
        else:
            info = '%s, %s' % (name, identifier)
        info = info.lower()
        # 2.1. check each keyword with user info
        match = True
        for kw in kw_array:
            if len(kw) > 0 > info.find(kw.lower()):
                match = False
                break
        if not match:
            continue
        # 2.2. check user meta
        meta = facebook.meta(identifier=identifier)
        if meta is None:
            # user meta not found, skip
            continue
        # 2.3. check limit
        index += 1
        if index < start:
            # skip
            continue
        elif index >= end:
            # mission accomplished
            break
        # got it
        users.append(identifier)
        if limit > 0:
            # get meta when limit is set
            results[str(identifier)] = meta.dictionary
    # 3. cache the search result
    g_search_cache.update(key=(keywords, start, end), value=(users, results), life_span=600, now=now)
    return users, results


# noinspection PyUnusedLocal
def save_response(facebook: CommonFacebook, station: ID, users: List[ID], results: dict) -> List[Content]:
    # TODO: Save online users in a text file
    for key in results:
        identifier = ID.parse(identifier=key)
        meta = Meta.parse(meta=results[key])
        if identifier is not None and meta is not None:
            # assert Meta.match_id(meta=meta, identifier=identifier), 'meta error'
            facebook.save_meta(meta=meta, identifier=identifier)
    # # store in redis server
    # for item in users:
    #     facebook.add_online_user(station=station, user=item)
    # # clear expired users
    # facebook.remove_offline_users(station=station, users=[])
    return []
