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

import time
from abc import abstractmethod
from typing import Optional, Union, List

from dimp import ID, SymmetricKey
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import Content, Command, MetaCommand, DocumentCommand, GroupCommand
from dimp import Packer, Processor, CipherKeyDelegate
from dimsdk import Messenger, MessengerDataSource

from ..utils import Log
from ..utils import Singleton

from .keystore import KeyStore
from .facebook import CommonFacebook


class CommonMessenger(Messenger):

    EXPIRES = 120  # query expires (2 minutes)

    def __init__(self):
        super().__init__()
        self.__context = {}
        # for checking duplicated queries
        self.__meta_queries = {}      # ID -> time
        self.__document_queries = {}  # ID -> time
        self.__group_queries = {}     # ID -> time

    def connected(self):
        pass

    @property
    def context(self) -> dict:
        return self.__context

    def get_context(self, key: str):
        return self.__context.get(key)

    @property
    def key_cache(self) -> CipherKeyDelegate:
        delegate = super().key_cache
        if delegate is None:
            """
                Key Store
                ~~~~~~~~~

                Memory cache for reused passwords (symmetric key)
            """
            delegate = KeyStore()
            Messenger.key_cache.__set__(self, delegate)
        return delegate

    @property
    def data_source(self) -> MessengerDataSource:
        delegate = super().data_source
        if delegate is None:
            delegate = MessageDataSource()
            Messenger.data_source.__set__(self, delegate)
        return delegate

    def _create_facebook(self) -> CommonFacebook:
        # facebook = CommonFacebook()
        # facebook.messenger = self
        # return facebook
        raise AssertionError('set facebook first')

    def _create_packer(self) -> Packer:
        from .packer import CommonPacker
        return CommonPacker(messenger=self)

    def _create_processor(self) -> Processor:
        from .processor import CommonProcessor
        return CommonProcessor(messenger=self)

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]) -> bool:
        if isinstance(msg, ReliableMessage):
            # check meta & document
            meta = self.facebook.meta(identifier=msg.sender)
            if meta is not None:
                self.facebook.document(identifier=msg.sender)
        return super().suspend_message(msg=msg)

    def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        try:
            return super().deserialize_content(data=data, key=key, msg=msg)
        except UnicodeDecodeError as error:
            self.error('failed to deserialize content: %s, %s' % (error, data))

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
    def _send_command(self, cmd: Command, receiver: Optional[ID] = None) -> bool:
        raise NotImplemented

    def query_meta(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__meta_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__meta_queries[identifier] = now
        # query from DIM network
        self.info('querying meta for %s' % identifier)
        cmd = MetaCommand(identifier=identifier)
        return self._send_command(cmd=cmd)

    def query_document(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__document_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__document_queries[identifier] = now
        # query from DIM network
        self.info('querying document for %s' % identifier)
        cmd = DocumentCommand(identifier=identifier)
        return self._send_command(cmd=cmd)

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: List[ID]) -> bool:
        now = time.time()
        last = self.__group_queries.get(group, 0)
        if (now - last) < self.EXPIRES:
            return False
        if len(users) == 0:
            return False
        self.__group_queries[group] = now
        # query from users
        cmd = GroupCommand.query(group=group)
        checking = False
        for item in users:
            if self._send_command(cmd=cmd, receiver=item):
                checking = True
        return checking


@Singleton
class MessageDataSource(MessengerDataSource):

    def save_message(self, msg: InstantMessage) -> bool:
        content = msg.content
        Log.info('TODO: saving msg: %s -> %s\n type=%d, text=%s\n %s' % (msg.sender, msg.receiver,
                                                                         content.type, content.get('text'),
                                                                         msg.get('traces')))
        return True

    def suspend_message(self, msg: Union[InstantMessage, ReliableMessage]) -> bool:
        Log.info('TODO: suspending msg: %s -> %s | %s' % (msg.sender, msg.receiver, msg.get('traces')))
        return True
