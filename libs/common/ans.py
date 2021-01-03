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
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""

from typing import Optional, Union

from dimp import ID, Address
from dimsdk import AddressNameService


class AddressNameServer(AddressNameService):

    def load(self):
        # TODO: load all ANS records from database
        pass

    def save(self, name: str, identifier: ID = None) -> bool:
        ok = super().save(name=name, identifier=identifier)
        # TODO: save new record into database
        return ok


class IDFactory(ID.Factory):

    def __init__(self):
        super().__init__()
        self.__ids = {}

    def create_identifier(self, address: Address, name: Optional[str]=None, terminal: Optional[str]=None) -> ID:
        return s_id_factory.create_identifier(address=address, name=name, terminal=terminal)

    def parse_identifier(self, identifier: Union[ID, str, None]) -> Optional[ID]:
        # try ANS record
        _id = s_ans.identifier(name=identifier)
        if _id is None:
            # parse by original factory
            _id = s_id_factory.parse_identifier(identifier=identifier)
        return _id


s_ans = AddressNameService()
s_id_factory = ID.factory()
ID.register(factory=IDFactory())
