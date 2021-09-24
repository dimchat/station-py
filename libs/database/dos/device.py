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
from typing import Optional, List

from dimp import ID

from .base import Storage


class DeviceStorage(Storage):
    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'device.js')

    def save_device(self, device: dict, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving device info into: %s' % path)
        return self.write_json(container=device, path=path)

    def device(self, identifier: ID) -> Optional[dict]:
        path = self.__path(identifier=identifier)
        self.info('Loading device from: %s' % path)
        return self.read_json(path=path)

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # get device info with ID
        device = self.device(identifier=identifier)
        device = append_device_token(device=device, token=token)
        if device is not None:
            return self.save_device(device=device, identifier=identifier)

    def device_tokens(self, identifier: ID) -> Optional[List[str]]:
        # get device info with ID
        device = self.device(identifier=identifier)
        if device is not None:
            return device.get('tokens')


def append_device_token(device: Optional[dict], token: str) -> Optional[dict]:
    if device is None:
        return {'tokens': [token]}
    # get tokens list for updating
    tokens: list = device.get('tokens')
    if tokens is None:
        # new device token
        tokens = [token]
    elif token in tokens:
        # already exists
        return None
    else:
        # keep only last three records
        while len(tokens) > 2:
            tokens.pop()
        tokens.insert(0, token)
    device['tokens'] = tokens
