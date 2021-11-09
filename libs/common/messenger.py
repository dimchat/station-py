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

from dimp import ID, SymmetricKey
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import ContentType, Content, FileContent
from dimp import Command, GroupCommand
from dimp import Packer, Processor, CipherKeyDelegate
from dimsdk import Messenger, Callback as MessengerCallback

from ..utils import Logging
from ..database import FrequencyChecker

from .keystore import KeyStore
from .facebook import CommonFacebook, SharedFacebook


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

    @abstractmethod
    def send_message_data(self, data: bytes, callback: Optional[MessengerCallback], priority: int = 0) -> bool:
        """
        Send out a message data package onto network

        :param data:     message data
        :param callback: completion handler
        :param priority: task priority (smaller is faster)
        :return: True on success
        """
        raise NotImplemented


class CommonMessenger(Messenger, Logging):

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 600  # seconds

    def __init__(self):
        super().__init__()
        self.__delegate: Optional[weakref.ReferenceType] = None
        self.__message_packer = None
        self.__message_processor = None
        self.__message_transmitter = None
        # for checking duplicated queries
        self.__group_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)

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

    @property
    def facebook(self) -> CommonFacebook:
        transceiver = super().facebook
        assert isinstance(transceiver, CommonFacebook), 'facebook error: %s' % transceiver
        return transceiver

    # Override
    def _create_facebook(self) -> CommonFacebook:
        return SharedFacebook()

    @property
    def key_cache(self) -> CipherKeyDelegate:
        delegate = super().key_cache
        if delegate is None:
            """ Key Store
                ~~~~~~~~~
                Memory cache for reused passwords (symmetric key)
            """
            delegate = KeyStore()
            Messenger.key_cache.__set__(self, delegate)
        return delegate

    #
    #   Message Packer
    #
    @property
    def packer(self) -> Messenger.Packer:
        delegate = super().packer
        if delegate is None:
            delegate = self.__get_packer()
        return delegate

    @packer.setter
    def packer(self, delegate: Messenger.Packer):
        Messenger.packer.__set__(self, delegate)
        from .packer import MessagePacker
        if isinstance(delegate, MessagePacker):
            self.__message_packer = delegate

    def __get_packer(self):  # -> MessagePacker:
        if self.__message_packer is None:
            self.__message_packer = self._create_packer()
        return self.__message_packer

    def _create_packer(self) -> Packer:
        from .packer import CommonPacker
        return CommonPacker(messenger=self)

    #
    #   Message Processor
    #
    @property
    def processor(self) -> Messenger.Processor:
        delegate = super().processor
        if delegate is None:
            delegate = self.__get_processor()
        return delegate

    @processor.setter
    def processor(self, delegate: Messenger.Processor):
        Messenger.processor.__set__(self, delegate)
        from .processor import MessageProcessor
        if isinstance(delegate, MessageProcessor):
            self.__message_processor = delegate

    def __get_processor(self):  # -> MessageProcessor
        if self.__message_processor is None:
            self.__message_processor = self._create_processor()
        return self.__message_processor

    def _create_processor(self) -> Processor:
        from .processor import CommonProcessor
        return CommonProcessor(messenger=self)

    #
    #   Message Transmitter
    #
    @property
    def transmitter(self) -> Messenger.Transmitter:
        delegate = super().transmitter
        if delegate is None:
            delegate = self.__get_transmitter()
        return delegate

    @transmitter.setter
    def transmitter(self, delegate: Messenger.Transmitter):
        Messenger.transmitter.__set__(self, delegate)
        from .transmitter import CommonTransmitter
        assert isinstance(delegate, CommonTransmitter), 'Transmitter error: %s' % delegate
        self.__message_transmitter = delegate

    def __get_transmitter(self):  # -> MessageTransmitter:
        if self.__message_transmitter is None:
            self.__message_transmitter = self._create_transmitter()
        return self.__message_transmitter

    def _create_transmitter(self):  # -> MessageTransmitter:
        from .transmitter import CommonTransmitter
        return CommonTransmitter(messenger=self)

    #
    #   FPU
    #
    def __file_content_processor(self):  # -> FileContentProcessor:
        processor = self.processor
        from .processor import CommonProcessor
        assert isinstance(processor, CommonProcessor), 'message processor error: %s' % processor
        cpu = processor.get_processor_by_type(msg_type=ContentType.FILE)
        from .cpu import FileContentProcessor
        assert isinstance(cpu, FileContentProcessor), 'failed to get file content processor'
        return cpu

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

    #
    #   Interfaces for Sending Commands
    #
    @abstractmethod
    def _send_command(self, cmd: Command, receiver: Optional[ID] = None) -> bool:
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
            if self._send_command(cmd=cmd, receiver=item):
                checking = True
        return checking

    #
    #   Interfaces for Station
    #
    def upload_encrypted_data(self, data: bytes, msg: InstantMessage) -> str:
        return self.delegate.upload_encrypted_data(data=data, msg=msg)

    def download_encrypted_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        return self.delegate.download_encrypted_data(url=url, msg=msg)

    def send_message_data(self, data: bytes, callback: Optional[MessengerCallback], priority: int = 0) -> bool:
        return self.delegate.send_message_data(data=data, callback=callback, priority=priority)

    #
    #   Events
    #
    def handshake_accepted(self, identifier: ID, client_address: tuple = None):
        """ callback after handshake success """
        raise NotImplemented
