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

from typing import Optional, Dict

from dimples import ID

from dimples.database.dos.base import template_replace
from dimples.database import GroupStorage as SuperStorage


class GroupStorage(SuperStorage):

    """
        Encrypted keys
        ~~~~~~~~~~~~~~
        
        file path: '.dim/private/{GROUP_ADDRESS}/group-keys-{SENDER_ADDRESS}.js
    """
    keys_path = '{PRIVATE}/{GROUP_ADDRESS}/group-keys-{SENDER_ADDRESS}.js'

    def show_info(self):
        super().show_info()
        path = template_replace(self.keys_path, 'PRIVATE', self._private)
        print('!!!  grp keys path: %s' % path)

    def __keys_path(self, group: ID, sender: ID) -> str:
        path = self.members_path
        path = template_replace(path, 'PRIVATE', self._private)
        path = template_replace(path, 'GROUP_ADDRESS', str(group.address))
        return template_replace(path, 'SENDER_ADDRESS', str(sender.address))

    def save_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        path = self.__keys_path(group=group, sender=sender)
        self.info('Saving group keys into: %s' % path)
        return self.write_json(container=keys, path=path)

    def load_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        path = self.__keys_path(group=group, sender=sender)
        self.info('Loading group keys from: %s' % path)
        return self.read_json(path=path)
