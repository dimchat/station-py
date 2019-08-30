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

from mkm import ID, Profile

from common import Log
from .storage import Storage


class ProfileTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches = {}

    """
        Profile for Accounts
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def __path(self, identifier: ID) -> str:
        directory = super().directory(control='public', identifier=identifier)
        return os.path.join(directory, 'profile.js')

    def __cache_profile(self, profile: Profile) -> bool:
        identifier = profile.identifier
        assert identifier.valid, 'profile ID not valid: %s' % profile
        if profile.valid:
            self.__caches[identifier] = profile
            return True

    def __load_profile(self, identifier: ID) -> Profile:
        path = self.__path(identifier=identifier)
        Log.info('Loading profile from: %s' % path)
        dictionary = super().read_json(path=path)
        if dictionary is not None:
            # compatible with v1.0
            data = dictionary.get('data')
            if data is None:
                data = dictionary.get('profile')
                if data is not None:
                    dictionary['data'] = data
                    dictionary.pop('profile')
        return Profile(dictionary)

    def __save_profile(self, profile: Profile) -> bool:
        identifier = profile.identifier
        assert identifier.valid, 'profile ID not valid: %s' % profile
        path = self.__path(identifier=identifier)
        Log.info('Saving profile into: %s' % path)
        return super().write_json(content=profile, path=path)

    def save_profile(self, profile: Profile) -> bool:
        if not self.__cache_profile(profile=profile):
            raise ValueError('failed to cache profile: %s' % profile)
        return self.__save_profile(profile=profile)

    def profile(self, identifier: ID) -> Profile:
        info = self.__caches.get(identifier)
        if info is None:
            info = self.__load_profile(identifier=identifier)
            if info is not None:
                self.__caches[identifier] = info
        return info


class DeviceTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches = {}

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def __path(self, identifier: ID) -> str:
        directory = super().directory(control='protected', identifier=identifier)
        return os.path.join(directory, 'device.js')

    def __cache_device(self, device: dict, identifier: ID) -> bool:
        assert identifier.valid, 'ID not valid: %s' % identifier
        self.__caches[identifier] = device
        return True

    def __load_device(self, identifier: ID) -> dict:
        path = self.__path(identifier=identifier)
        Log.info('Loading device info from: %s' % path)
        return super().read_json(path=path)

    def __save_device(self, device: dict, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        if super().exists(path=path):
            # device file already exists
            return True
        Log.info('Saving device info into: %s' % path)
        return super().write_json(content=device, path=path)

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # get device info with ID
        # 1. check from caches
        # 2. load from storage
        device = self.__load_device(identifier=identifier)
        if device is None:
            device = {}
        # get tokens list for updating
        tokens = device.get('tokens')
        if tokens is None:
            # new device token
            tokens = [token]
        elif token in tokens:
            # already exists
            return False
        else:
            # append token
            # TODO: keep only last two records
            tokens.append(token)
        device['tokens'] = tokens
        if not self.__cache_device(device=device, identifier=identifier):
            raise ValueError('failed to cache device info for: %s, %s' % (identifier, device))
        return self.__save_device(device=device, identifier=identifier)

    def device_tokens(self, identifier: ID) -> list:
        # 1. get from cache
        device = self.__caches.get(identifier)
        if device is not None:
            return device.get('token')
        # 2. load from storage
        device = self.__load_device(identifier=identifier)
        if device is not None:
            self.__cache_device(device=device, identifier=identifier)
            return device.get('token')
