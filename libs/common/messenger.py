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
import weakref
from abc import abstractmethod
from typing import Optional, Union, List

from startrek import DeparturePriority

from dimp import ID, SymmetricKey
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import ContentType, Content, FileContent
from dimp import Command, GroupCommand
from dimp import Packer, Processor
from dimsdk import Messenger, CipherKeyDelegate

from ..utils import Logging
from ..database import FrequencyChecker

from .keycache import KeyCache
from .facebook import CommonFacebook, SharedFacebook
from .session import BaseSession


class MessengerDelegate:

    @abstractmethod
    def upload_encrypted_data(self, data: bytes, msg: InstantMessage) -> str:
        """
        Upload encrypted data to CDN

        :param data: encrypted file data
        :param msg:  instant message
        :return: download URL
        """
        raise NotImplemented

    @abstractmethod
    def download_encrypted_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        """
        Download encrypted data from CDN

        :param url: download URL
        :param msg: instant message
        :return: encrypted file data
        """
        raise NotImplemented


class CommonMessenger(Messenger, Logging):

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 600  # seconds

    def __init__(self):
        super().__init__()
        self.__delegate: Optional[weakref.ReferenceType] = None
        self.__message_packer = self._create_packer()
        self.__message_processor = self._create_processor()
        self.packer = self.__message_packer
        self.processor = self.__message_processor
        self.facebook = self._create_facebook()
        self.key_cache = self._create_key_cache()
        # for checking duplicated queries
        self.__group_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)

    def _create_facebook(self) -> CommonFacebook:
        return SharedFacebook()

    # noinspection PyMethodMayBeStatic
    def _create_key_cache(self) -> CipherKeyDelegate:
        return KeyCache()

    def _create_packer(self) -> Packer:
        from .packer import CommonPacker
        return CommonPacker(messenger=self)

    def _create_processor(self) -> Processor:
        from .processor import CommonProcessor
        return CommonProcessor(messenger=self)

    @property  # Override
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @facebook.setter  # Override
    def facebook(self, barrack: CommonFacebook):
        Messenger.facebook.__set__(self, barrack)

    @property
    def session(self) -> BaseSession:
        raise NotImplemented

    #
    #   Delegate for sending data
    #
    @property
    def delegate(self) -> Optional[MessengerDelegate]:
        if self.__delegate is not None:
            return self.__delegate()

    @delegate.setter
    def delegate(self, value: Optional[MessengerDelegate]):
        self.__delegate = weakref.ref(value)

    #
    #   FPU
    #
    def __file_content_processor(self):  # -> FileContentProcessor:
        processor = self.processor
        from .processor import CommonProcessor
        assert isinstance(processor, CommonProcessor), 'message processor error: %s' % processor
        fpu = processor.get_processor_by_type(msg_type=ContentType.FILE)
        from .cpu import FileContentProcessor
        assert isinstance(fpu, FileContentProcessor), 'failed to get file content processor'
        return fpu

    # Override
    def serialize_content(self, content: Content, key: SymmetricKey, msg: InstantMessage) -> bytes:
        # check attachment for File/Image/Audio/Video message content before
        if isinstance(content, FileContent):
            fpu = self.__file_content_processor()
            fpu.upload(content=content, password=key, msg=msg)
        return super().serialize_content(content=content, key=key, msg=msg)

    # Override
    def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        try:
            content = super().deserialize_content(data=data, key=key, msg=msg)
        except UnicodeDecodeError as error:
            self.error('failed to deserialize content: %s, %s' % (error, data))
            return None
        if content is None:
            raise AssertionError('failed to deserialize message content: %s' % msg)
        # check attachment for File/Image/Audio/Video message content after
        if isinstance(content, FileContent):
            fpu = self.__file_content_processor()
            fpu.download(content=content, password=key, msg=msg)
        return content

    #
    #   Reuse message key
    #

    # Override
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

    # Override
    def encrypt_key(self, data: bytes, receiver: ID, msg: InstantMessage) -> Optional[bytes]:
        pk = self.facebook.public_key_for_encryption(identifier=receiver)
        if pk is None:
            # save this message in a queue waiting receiver's meta response
            self.suspend_message(msg=msg)
            # raise LookupError('failed to get encrypt key for receiver: %s' % receiver)
            return None
        return super().encrypt_key(data=data, receiver=receiver, msg=msg)

    #
    #   Interfaces for Message Storage
    #

    def save_message(self, msg: InstantMessage) -> bool:
        """
        Save the message into local storage

        :param msg: instant message
        :return: False on error
        """
        sender = msg.sender
        receiver = msg.receiver
        when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg.time))
        content = msg.content
        command = content.get('command')
        text = content.get('text')
        traces = msg.get('traces')
        self.info('TODO: saving msg: %s -> %s\n time=[%s] type=%d, command=%s, text=%s traces=%s' %
                  (sender, receiver, when, content.type, command, text, traces))
        return True

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]) -> bool:
        """
        1. Suspend the sending message for the receiver's meta & visa,
           or group meta when received new message
        2. Suspend the received message for the sender's meta

        :param msg: instant/reliable message
        :return: False on error
        """
        sender = msg.sender
        receiver = msg.receiver
        when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg.time))
        traces = msg.get('traces')
        self.warning('TODO: suspending msg: %s -> %s\n time=[%s] traces=%s' % (sender, receiver, when, traces))
        return True

    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        return self.session.send_reliable_message(msg=msg, priority=priority)

    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        return self.session.send_instant_message(msg=msg, priority=priority)

    def send_content(self, content: Content, priority: int, receiver: ID, sender: ID = None) -> bool:
        return self.session.send_content(content=content, priority=priority, receiver=receiver, sender=sender)

    #
    #   Interfaces for Sending Commands
    #
    @abstractmethod
    def send_command(self, cmd: Command, priority: int, receiver: Optional[ID] = None) -> bool:
        raise NotImplemented

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: List[ID]) -> bool:
        if len(users) == 0 or not self.__group_queries.expired(key=group):
            return False
        # current user ID
        current = self.facebook.current_user.identifier
        # query from users
        cmd = GroupCommand.query(group=group)
        checking = False
        for item in users:
            if item == current:
                continue
            if self.send_command(cmd=cmd, priority=DeparturePriority.SLOWER, receiver=item):
                checking = True
        return checking

    #
    #   Interfaces for Station
    #
    def upload_encrypted_data(self, data: bytes, msg: InstantMessage) -> str:
        return self.delegate.upload_encrypted_data(data=data, msg=msg)

    def download_encrypted_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        return self.delegate.download_encrypted_data(url=url, msg=msg)

    #
    #   Events
    #
    def handshake_accepted(self, identifier: ID, client_address: tuple = None):
        """ callback after handshake success """
        raise NotImplemented
