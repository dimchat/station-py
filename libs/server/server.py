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
    Station Server
    ~~~~~~~~~~~~~~

    Local station
"""

import os

from dimp import ID, Meta, Station
from dimp import Content, InstantMessage, SecureMessage, ReliableMessage

from ..common import Storage, Facebook, Messenger


def save_freshman(identifier: ID) -> bool:
    """ Save freshman ID in a text file for the robot

        file path: '.dim/freshmen.txt'
    """
    path = os.path.join(Storage.root, 'freshmen.txt')
    line = identifier + '\n'
    Storage.info('saving freshman: %s' % identifier)
    return Storage.append_text(text=line, path=path)


class Server(Station):
    """
        Local Station
        ~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int=9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.messenger: Messenger = None
        self.running = False

    def pack(self, content: Content, receiver: ID) -> ReliableMessage:
        """ Pack message from this station """
        i_msg = InstantMessage.new(content=content, sender=self.identifier, receiver=receiver)
        r_msg = self.messenger.encrypt_sign(msg=i_msg)
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
                save_freshman(identifier=sender)
        return self.messenger.verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage) -> InstantMessage:
        """ Decrypt message for this station """
        s_msg = msg.trim(self.identifier)
        return self.messenger.decrypt_message(msg=s_msg)

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
