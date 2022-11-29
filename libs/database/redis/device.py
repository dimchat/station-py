# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from typing import List, Optional

from dimsdk import json_encode, json_decode, utf8_encode, utf8_decode
from dimsdk import ID

from ..dos.device import append_device_token

from .base import Cache


class DeviceCache(Cache):

    # device info cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'user'

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dim.user.{ID}.device'
    """
    def __device_key(self, identifier: ID) -> str:
        return '%s.%s.%s.device' % (self.database, self.table, identifier)

    def save_device(self, device: dict, identifier: ID) -> bool:
        value = json_encode(obj=device)
        value = utf8_encode(string=value)
        name = self.__device_key(identifier=identifier)
        self.set(name=name, value=value, expires=self.EXPIRES)
        return True

    def device(self, identifier: ID) -> Optional[dict]:
        name = self.__device_key(identifier=identifier)
        value = self.get(name=name)
        if value is not None:
            value = utf8_decode(data=value)
            return json_decode(string=value)

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
