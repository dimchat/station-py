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
    Common extensions for Facebook
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from typing import Optional, List

from dimples import PrivateKey
from dimples import ID
from dimples.common import CommonFacebook as SuperFacebook


class CommonFacebook(SuperFacebook):

    def __init__(self):
        super().__init__()
        self.__group_assistants = []

    #
    #   Contacts
    #

    def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        db = self.database
        return db.save_contacts(contacts=contacts, identifier=identifier)

    #
    #   Private Keys
    #

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        db = self.database
        return db.save_private_key(key=key, identifier=identifier, key_type=key_type)

    #
    #    GroupDataSource
    #

    # Override
    def assistants(self, identifier: ID) -> Optional[List[ID]]:
        array = super().assistants(identifier=identifier)
        if array is not None and len(array) > 0:
            return array
        # get from global setting
        if len(self.__group_assistants) > 0:
            return self.__group_assistants
        # get from ANS
        bot = ID.parse(identifier='assistant')
        if bot is not None:
            return [bot]

    def add_assistant(self, assistant: ID):
        if assistant not in self.__group_assistants:
            if assistant == ID.parse(identifier='assistant'):
                self.__group_assistants.insert(0, assistant)
            else:
                self.__group_assistants.append(assistant)
