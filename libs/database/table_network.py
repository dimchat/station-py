# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from typing import Optional, List

from dimp import ID

from .redis import NetworkCache


class NetworkTable:

    def __init__(self):
        super().__init__()
        self.__redis = NetworkCache()

    def add_meta_query(self, identifier: ID):
        self.__redis.add_meta_query(identifier=identifier)

    def pop_meta_query(self) -> Optional[ID]:
        return self.__redis.pop_meta_query()

    def add_document_query(self, identifier: ID):
        self.__redis.add_document_query(identifier=identifier)

    def pop_document_query(self) -> Optional[ID]:
        return self.__redis.pop_document_query()

    def add_online_user(self, station: ID, user: ID, login_time: int = None):
        self.__redis.add_online_user(station=station, user=user, login_time=login_time)

    def remove_offline_users(self, station: ID, users: List[ID]):
        self.__redis.remove_offline_users(station=station, users=users)

    def get_online_users(self, station: ID, start: int = 0, limit: int = -1) -> List[ID]:
        return self.__redis.get_online_users(station=station, start=start, limit=limit)
