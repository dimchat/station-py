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

from dimp import ID, ReliableMessage
from dimsdk import LoginCommand

from .storage import Storage


class LoginTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = {}

    """
        Login info for Users
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/login.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'login.js')

    def __cache_login(self, cmd: LoginCommand, sender: ID, msg: ReliableMessage) -> bool:
        assert cmd.station is not None, 'login station error: %s' % cmd
        info = self.__caches.get(sender)
        if info is not None:
            old = info.get('cmd')
            if old is not None:
                # check login time
                if cmd.time <= old.time:
                    return False
        assert sender == cmd.identifier, 'login ID not valid: %s' % cmd
        assert sender == msg.sender, 'login ID not valid: %s' % msg
        self.__caches[sender] = {'cmd': cmd, 'msg': msg}
        return True

    def __load_login(self, identifier: ID) -> dict:
        path = self.__path(identifier=identifier)
        self.info('Loading login from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is None:
            return {}
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        return {
            'cmd': LoginCommand(cmd),
            'msg': ReliableMessage.parse(msg=msg),
        }

    def __save_login(self, cmd: LoginCommand, sender: ID, msg: ReliableMessage) -> bool:
        path = self.__path(identifier=sender)
        self.info('Saving login into: %s' % path)
        return self.write_json(container={'cmd': cmd, 'msg': msg}, path=path)

    def save_login(self, cmd: LoginCommand, sender: ID, msg: ReliableMessage) -> bool:
        if not self.__cache_login(cmd=cmd, sender=sender, msg=msg):
            # raise ValueError('failed to cache login: %s -> %s, %s' % (sender, cmd, msg))
            self.error('failed to cache login: %s -> %s' % (sender, cmd))
            return False
        return self.__save_login(cmd=cmd, sender=sender, msg=msg)

    def login_command(self, identifier: ID) -> LoginCommand:
        # 1. get from cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. load from storage
            info = self.__load_login(identifier=identifier)
            # 3. update memory cache
            self.__caches[identifier] = info
        return info.get('cmd')

    def login_message(self, identifier: ID) -> ReliableMessage:
        # 1. get from cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. load from storage
            info = self.__load_login(identifier=identifier)
            # 3. update memory cache
            self.__caches[identifier] = info
        return info.get('msg')
