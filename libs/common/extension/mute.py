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
    Mute Protocol
    ~~~~~~~~~~~~~

    Mute all messages(skip Pushing Notification) in this conversation, which ID(user/group) contains in 'list'.
    If value of 'list' is None, means querying mute-list from station
"""

from dimp import ID, HistoryCommand
from dimp.protocol.command import command_classes


class MuteCommand(HistoryCommand):
    """
        Mute Command
        ~~~~~~~~~~~~

        data format: {
            type : 0x89,
            sn   : 123,

            command : "mute", // command name
            time    : 0,      // command timestamp
            list    : []      // mute-list
        }
    """

    MUTE = 'mute'

    def __new__(cls, cmd: dict):
        """
        Create mute command

        :param cmd: command info
        :return: MuteCommand object
        """
        if cmd is None:
            return None
        elif cls is MuteCommand:
            if isinstance(cmd, MuteCommand):
                # return MuteCommand object directly
                return cmd
        # new MuteCommand(dict)
        return super().__new__(cls, cmd)

    def __init__(self, content: dict):
        if self is content:
            # no need to init again
            return
        super().__init__(content)
        # mute-list
        self.__list: list = None

    #
    #   mute-list
    #
    @property
    def mute_list(self) -> list:
        if self.__list is None:
            # TODO: convert values to ID objects
            self.__list = self.get('list')
        return self.__list

    @mute_list.setter
    def mute_list(self, value: list):
        if value is None:
            self.pop('list', None)
        else:
            self['list'] = value
        self.__list = value

    def add_identifier(self, identifier: ID) -> bool:
        if self.mute_list is None:
            self.__list = []
            self['list'] = self.__list
        elif identifier in self.__list:
            # raise AssertionError('ID already exists: %s' % identifier)
            return False
        self.__list.append(identifier)
        return True

    def remove_identifier(self, identifier: ID) -> bool:
        if self.__list is None:
            return False
        elif identifier not in self.__list:
            return False
        self.__list.remove(identifier)
        return True

    #
    #   Factories
    #
    @classmethod
    def new(cls, content: dict=None, mute: list=None):
        """
        Create mute command

        :param content: command info
        :param mute: mute-list
        :return: MuteCommand object
        """
        if content is None:
            # create empty content
            content = {}
        # set mute-list
        if mute is not None:
            content['list'] = mute
        # new MuteCommand(dict)
        return super().new(content=content, command=cls.MUTE)


# register command class
command_classes[MuteCommand.MUTE] = MuteCommand
