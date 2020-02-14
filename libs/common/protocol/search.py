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

from dimp import Command


class SearchCommand(Command):
    """
        Search Command
        ~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            command  : "search",        // or "users"

            keywords : "keywords",      // keyword string
            users    : ["ID",],         // user ID list
            results  : {"ID": {meta}, } // user's meta map
        }
    """

    SEARCH = 'search'

    ONLINE_USERS = 'users'

    def __new__(cls, cmd: dict):
        """
        Create search command

        :param cmd: command info
        :return: SearchCommand object
        """
        if cmd is None:
            return None
        elif cls is SearchCommand:
            if isinstance(cmd, SearchCommand):
                # return SearchCommand object directly
                return cmd
        # new SearchCommand(dict)
        return super().__new__(cls, cmd)

    def __init__(self, content: dict):
        if self is content:
            # no need to init again
            return
        super().__init__(content)

    #
    #   User ID list
    #
    @property
    def users(self) -> list:
        return self.get('users')

    @users.setter
    def users(self, value):
        if value is None:
            self.pop('users', None)
        else:
            self['users'] = value

    #
    #   User's meta map
    #
    @property
    def results(self) -> str:
        return self.get('results')

    @results.setter
    def results(self, value):
        if value is None:
            self.pop('results', None)
        else:
            self['results'] = value

    #
    #   Factories
    #
    @classmethod
    def new(cls, content: dict=None, keywords: str=None, users: list=None, results: dict=None):
        """
        Create search command

        :param content: command info
        :param keywords: search number, ID, or 'users'
        :param users: user ID list
        :param results: user meta map
        :return: SearchCommand object
        """
        if content is None:
            # create empty content
            content = {}
        # new SearchCommand(dict)
        if keywords is None:
            command = cls.SEARCH
        elif keywords == cls.SEARCH or keywords == cls.ONLINE_USERS:
            command = keywords
        else:
            command = cls.SEARCH
            content['keywords'] = keywords
        if users is not None:
            content['users'] = users
        if results is not None:
            content['results'] = results
        return super().new(content=content, command=command)


# register command class
Command.register(command=SearchCommand.SEARCH, command_class=SearchCommand)
Command.register(command=SearchCommand.ONLINE_USERS, command_class=SearchCommand)
