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
    Block Protocol
    ~~~~~~~~~~~~~~

    Ignore all messages in this conversation, which ID(user/group) contains in 'list'.
    If value of 'list' is None, means querying block-list from station
"""

from typing import Union

from dimp import ID, HistoryCommand
from dimp.protocol.command import command_classes


class BlockCommand(HistoryCommand):
    """
        Block Command
        ~~~~~~~~~~~~~

        data format: {
            type : 0x89,
            sn   : 123,

            command : "block", // command name
            time    : 0,       // command timestamp
            list    : []       // block-list
        }
    """

    BLOCK = 'block'

    def __init__(self, content: dict):
        super().__init__(content)
        self.__list: list = None

    #
    #   block-list
    #
    @property
    def block_list(self) -> list:
        if self.__list is None:
            # TODO: convert values to ID objects
            self.__list = self.get('list')
        return self.__list

    @block_list.setter
    def block_list(self, value: list):
        if value is None:
            self.pop('list', None)
        else:
            self['list'] = value
        self.__list = value

    def add_identifier(self, identifier: ID) -> bool:
        if self.block_list is None:
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
    #   Factory
    #
    @classmethod
    def new(cls, block: Union[list, dict, None]):
        if block is None:
            content = {
                'command': BlockCommand.BLOCK,
            }
        elif isinstance(block, list):
            content = {
                'command': BlockCommand.BLOCK,
                'list': block,
            }
        elif isinstance(block, dict):
            content = block
        else:
            raise TypeError('block command argument error: %s' % block)
        return HistoryCommand.new(content)


# register command class
command_classes[BlockCommand.BLOCK] = BlockCommand
