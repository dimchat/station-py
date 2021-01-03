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
    Common extensions for Messenger
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from abc import abstractmethod
from typing import Optional, Union

from dimp import ID, SymmetricKey
from dimp import InstantMessage

from dimsdk import Messenger, Packer, Processor

from .utils import Log

from .keystore import KeyStore
from .facebook import CommonFacebook


class CommonMessenger(Messenger):

    def __init__(self):
        super().__init__()
        self.key_cache = KeyStore()
        self.__context = {}

    @property
    def context(self) -> dict:
        return self.__context

    def get_context(self, key: str):
        return self.__context.get(key)

    def set_context(self, key: str, value):
        if value is None:
            self.__context.pop(key, None)
        else:
            self.__context[key] = value

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    def _create_packer(self) -> Packer:
        from .packer import CommonPacker
        return CommonPacker(messenger=self)

    def _create_processor(self) -> Processor:
        from .processor import CommandProcessor
        return CommandProcessor(messenger=self)

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    #
    #   Reuse message key
    #
    def serialize_key(self, key: Union[dict, SymmetricKey], msg: InstantMessage) -> Optional[bytes]:
        reused = key.get('reused')
        if reused is not None:
            if msg.receiver.is_group:
                # reuse key for grouped message
                return None
            # remove before serialize key
            key.pop('reused', None)
        data = super().serialize_key(key=key, msg=msg)
        if reused is not None:
            # put it back
            key['reused'] = reused
        return data

    #
    #   Interfaces for Sending Commands
    #
    @abstractmethod
    def query_meta(self, identifier: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def query_profile(self, identifier: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def query_group(self, group: ID, users: list) -> bool:
        raise NotImplemented
