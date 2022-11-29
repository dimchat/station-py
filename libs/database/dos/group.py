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

import os
from typing import Optional, List, Dict

from dimp import ID

from .base import Storage


class GroupStorage(Storage):
    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
    """
    def __members_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'members.txt')

    def save_members(self, members: List[ID], group: ID) -> bool:
        assert len(members) > 0, 'group members should not be empty: %s' % group
        path = self.__members_path(identifier=group)
        self.info('Saving members into: %s' % path)
        members = ID.revert(members=members)
        text = '\n'.join(members)
        return self.write_text(text=text, path=path)

    def members(self, group: ID) -> List[ID]:
        # 2. try from local storage
        path = self.__members_path(identifier=group)
        self.info('Loading members from: %s' % path)
        text = self.read_text(path=path)
        if text is None:
            return []
        else:
            return ID.convert(members=text.splitlines())

    def founder(self, group: ID) -> ID:
        # TODO: get founder
        pass

    def owner(self, group: ID) -> ID:
        # TODO: get owner
        pass

    """
        Encrypted keys
        ~~~~~~~~~~~~~~
        
        file path: '.dim/protected/{GROUP_ADDRESS}/group-keys-{SENDER_ADDRESS}.json
    """
    def __keys_path(self, group: ID, sender: ID) -> str:
        filename = 'group-keys-%s.js' % str(sender.address)
        return os.path.join(self.root, 'protected', str(group.address), filename)

    def save_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        path = self.__keys_path(group=group, sender=sender)
        self.info('Saving group keys into: %s' % path)
        return self.write_json(container=keys, path=path)

    def load_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        path = self.__keys_path(group=group, sender=sender)
        self.info('Loading group keys from: %s' % path)
        return self.read_json(path=path)
