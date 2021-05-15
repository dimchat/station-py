# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Search Protocol
    ~~~~~~~~~~~~~~~

    Search users with keywords
"""

from typing import Optional, Union, List

from dimp import ID, Command
from dimp.protocol import CommandFactoryBuilder


class SearchCommand(Command):
    """
        Search Command
        ~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            command  : "search",        // or "users"
            keywords : "keywords",      // keyword string

            start    : 0,
            limit    : 20,

            station  : "STATION_ID",    // station ID
            users    : ["ID",],         // user ID list
            results  : {"ID": {meta}, } // user's meta map
        }
    """

    SEARCH = 'search'

    ONLINE_USERS = 'users'

    def __init__(self, cmd: Optional[dict] = None, keywords: str = None, users: List[ID] = None, results: dict = None):
        if cmd is None:
            super().__init__(command=SearchCommand.SEARCH)
        else:
            super().__init__(cmd=cmd)
        # keywords
        if keywords is not None:
            self['keywords'] = keywords
        # users
        if users is not None:
            self['users'] = ID.revert(members=users)
        self.__users = users
        # results
        if results is not None:
            self['results'] = results
        self.__results = results

    #
    #   Keywords
    #
    @property
    def keywords(self) -> Optional[str]:
        kw = self.get('keywords')
        if kw is not None:
            return kw
        elif self.command == SearchCommand.ONLINE_USERS:
            return SearchCommand.ONLINE_USERS

    @keywords.setter
    def keywords(self, value: Union[str, list]):
        if isinstance(value, list):
            self['keywords'] = ' '.join(value)
        else:
            self['keywords'] = value

    @property
    def start(self) -> int:
        value = self.get('start')
        if value is None:
            return 0
        else:
            return int(value)

    @start.setter
    def start(self, value: int):
        self['start'] = value

    @property
    def limit(self) -> int:
        value = self.get('limit')
        if value is None:
            return 20
        else:
            return int(value)

    @limit.setter
    def limit(self, value: int):
        self['limit'] = value

    #
    #   Station ID
    #
    @property
    def station(self) -> Optional[ID]:
        return ID.parse(identifier=self.get('station'))

    @station.setter
    def station(self, identifier: ID):
        if identifier is None:
            self.pop('station', None)
        else:
            self['station'] = str(identifier)

    #
    #   User ID list
    #
    @property
    def users(self) -> Optional[List[ID]]:
        if self.__users is None:
            array = self.get('users')
            if isinstance(array, list):
                self.__users = ID.convert(members=array)
        return self.__users

    @users.setter
    def users(self, value: List[ID]):
        if value is None:
            self.pop('users', None)
        else:
            self['users'] = ID.revert(members=value)
        self.__users = value

    #
    #   User's meta map
    #
    @property
    def results(self) -> dict:
        return self.get('results')

    @results.setter
    def results(self, value: dict):
        if value is None:
            self.pop('results', None)
        else:
            self['results'] = value


# register
Command.register(command=SearchCommand.SEARCH, factory=CommandFactoryBuilder(command_class=SearchCommand))
Command.register(command=SearchCommand.ONLINE_USERS, factory=CommandFactoryBuilder(command_class=SearchCommand))
