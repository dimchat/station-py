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
from typing import Optional

from dimp import ID, Profile

from .storage import Storage


class ProfileTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = {}

    """
        Profile for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/profile.js'
        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'profile.js')

    def __cache_profile(self, profile: Profile) -> bool:
        identifier = Storage.identifier(profile.identifier)
        assert identifier.valid, 'profile ID not valid: %s' % profile
        if profile.valid:
            self.__caches[identifier] = profile
            return True

    def __load_profile(self, identifier: ID) -> Profile:
        path = self.__path(identifier=identifier)
        self.info('Loading profile from: %s' % path)
        dictionary = self.read_json(path=path)
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
        identifier = Storage.identifier(profile.identifier)
        assert identifier.valid, 'profile ID not valid: %s' % profile
        path = self.__path(identifier=identifier)
        self.info('Saving profile into: %s' % path)
        return self.write_json(container=profile, path=path)

    def save_profile(self, profile: Profile) -> bool:
        if not self.__cache_profile(profile=profile):
            # raise ValueError('failed to cache profile: %s' % profile)
            self.error('failed to cache profile: %s' % profile)
            return False
        return self.__save_profile(profile=profile)

    def profile(self, identifier: ID) -> Optional[Profile]:
        # 1. get from cache
        info = self.__caches.get(identifier)
        if info is not None:
            # if 'data' not in info:
            #     self.info('empty profile: %s' % info)
            return info
        # 2. load from storage
        info = self.__load_profile(identifier=identifier)
        if info is None:
            # place an empty profile for cache
            info = Profile.new(identifier=identifier)
        # 3. update memory cache
        self.__caches[identifier] = info
        return info


class DeviceTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = {}

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'device.js')

    def __cache_device(self, device: dict, identifier: ID) -> bool:
        assert identifier.valid, 'ID not valid: %s' % identifier
        self.__caches[identifier] = device
        return True

    def __load_device(self, identifier: ID) -> dict:
        path = self.__path(identifier=identifier)
        self.info('Loading device info from: %s' % path)
        return self.read_json(path=path)

    def __save_device(self, device: dict, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving device info into: %s' % path)
        return self.write_json(container=device, path=path)

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
            return True
        else:
            # append token
            # TODO: keep only last two records
            tokens.append(token)
        device['tokens'] = tokens
        if not self.__cache_device(device=device, identifier=identifier):
            raise ValueError('failed to cache device info for: %s, %s' % (identifier, device))
            # self.error('failed to cache device info for: %s, %s' % (identifier, device))
            # return False
        return self.__save_device(device=device, identifier=identifier)

    def device_tokens(self, identifier: ID) -> list:
        # 1. get from cache
        device = self.__caches.get(identifier)
        if device is not None:
            return device.get('tokens')
        # 2. load from storage
        device = self.__load_device(identifier=identifier)
        if device is not None:
            # 3. update memory cache
            self.__cache_device(device=device, identifier=identifier)
            return device.get('tokens')
