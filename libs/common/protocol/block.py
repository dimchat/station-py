# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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

from typing import Optional, Any, Dict, List

from dimsdk import ID, BaseCommand


class BlockCommand(BaseCommand):
    """
        Block Command
        ~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            cmd     : "block", // command name
            list    : []       // block-list
        }
    """

    BLOCK = 'block'

    def __init__(self, content: Optional[Dict[str, Any]] = None):
        if content is None:
            super().__init__(cmd=BlockCommand.BLOCK)
        else:
            super().__init__(content=content)

    #
    #   block-list
    #
    @property
    def block_list(self) -> Optional[List[ID]]:
        array = self.get('list')
        if array is not None:
            return ID.convert(members=array)

    @block_list.setter
    def block_list(self, value: List[ID]):
        if value is None:
            self.pop('list', None)
        else:
            self['list'] = ID.revert(members=value)
