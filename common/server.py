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
import time

from dimp import ID, Meta, Station
from dimp import Envelope, Content, InstantMessage, SecureMessage, ReliableMessage

from database import Storage
from .facebook import Facebook
from .messenger import Messenger


def save_freshmen(identifier: ID) -> bool:
    """ Save freshmen ID in a text file for the robot

        file path: '.dim/freshmen.txt'
    """
    path = os.path.join(Storage.root, 'freshmen.txt')
    line = identifier + '\n'
    return Storage.append_text(text=line, path=path)


class Server(Station):
    """
        Local Station
        ~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int=9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.running = False
        self.messenger: Messenger = None

    def pack(self, receiver: ID, content: Content) -> ReliableMessage:
        """ Pack message from this station """
        timestamp = int(time.time())
        env = Envelope.new(sender=self.identifier, receiver=receiver, time=timestamp)
        i_msg = InstantMessage.new(content=content, envelope=env)
        r_msg = self.messenger.encrypt_sign(i_msg)
        return r_msg

    def verify_message(self, msg: ReliableMessage) -> SecureMessage:
        """ Verify message data and signature """
        # check new user for the robot
        facebook: Facebook = self.delegate
        sender = facebook.identifier(msg.envelope.sender)
        meta = facebook.meta(identifier=sender)
        if meta is None:
            meta = Meta(msg.meta)
            if meta is not None and meta.match_identifier(sender):
                # new user
                save_freshmen(identifier=sender)
        return self.messenger.verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage) -> Content:
        """ Decrypt message for this station """
        s_msg = msg.trim(self.identifier)
        i_msg = self.messenger.decrypt_message(msg=s_msg)
        return i_msg.content

    def sign(self, data: bytes) -> bytes:
        facebook: Facebook = self.delegate
        key = facebook.private_key_for_signature(identifier=self.identifier)
        if key is not None:
            return key.sign(data=data)

    def decrypt(self, data: bytes) -> bytes:
        facebook: Facebook = self.delegate
        keys = facebook.private_keys_for_decryption(identifier=self.identifier)
        plaintext = None
        for key in keys:
            try:
                plaintext = key.decrypt(data=data)
            except ValueError:
                # If the dat length is incorrect
                continue
            if plaintext is not None:
                # decryption success
                break
        return plaintext
