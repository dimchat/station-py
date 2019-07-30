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

import time

import dimp
from dimp import ID, Meta
from dimp import Envelope, Content, InstantMessage, SecureMessage, ReliableMessage
from dimp import Transceiver


class Station(dimp.Station):

    def __init__(self, identifier: ID, host: str, port: int=9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.running = False
        self.transceiver: Transceiver = None

    def pack(self, receiver: ID, content: Content) -> ReliableMessage:
        """ Pack message from this station """
        timestamp = int(time.time())
        env = Envelope.new(sender=self.identifier, receiver=receiver, time=timestamp)
        i_msg = InstantMessage.new(content=content, envelope=env)
        r_msg = self.transceiver.encrypt_sign(i_msg)
        return r_msg

    def verify_message(self, msg: ReliableMessage) -> SecureMessage:
        # check meta (first contact?)
        meta = msg.meta
        if meta is not None:
            meta = Meta(meta)
            identifier = ID(msg.envelope.sender)
            # save meta for sender
            self.delegate.save_meta(identifier=identifier, meta=meta)
        # message delegate
        if msg.delegate is None:
            msg.delegate = self.transceiver
        return msg.verify()

    def decrypt_message(self, msg: SecureMessage) -> Content:
        """ Decrypt message for this station """
        s_msg = msg.trim(self.identifier)
        s_msg.delegate = self.transceiver
        i_msg = s_msg.decrypt()
        content = i_msg.content
        return content

    def sign(self, data: bytes) -> bytes:
        key = self.delegate.private_key_for_signature(identifier=self.identifier)
        if key is not None:
            return key.sign(data=data)

    def decrypt(self, data: bytes) -> bytes:
        keys = self.delegate.private_keys_for_decryption(identifier=self.identifier)
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
