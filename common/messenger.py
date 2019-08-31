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
    Messenger
    ~~~~~~~~~

    Transform and send message
"""

from dimp import Meta
from dimp import InstantMessage, ReliableMessage, ContentType, ForwardContent
from dimp import Transceiver, ITransceiverDelegate, ICompletionHandler

from .facebook import Facebook


class Messenger(Transceiver, ITransceiverDelegate):

    def __init__(self):
        super().__init__()
        self.delegate = self

    def verify_decrypt(self, msg: ReliableMessage):
        # 0. [Meta Protocol] check meta in first contact message
        sender = self.barrack.identifier(msg.envelope.sender)
        meta = self.barrack.meta(identifier=sender)
        if meta is None:
            # first contact, try meta in message package
            meta = Meta(msg.meta)
            if meta is None:
                # TODO: query meta for sender from DIM network
                raise LookupError('failed to get meta for sender: %s' % sender)
            assert meta.match_identifier(identifier=sender), 'meta not match: %s, %s' % (sender, meta)
            facebook: Facebook = self.barrack
            if not facebook.save_meta(meta=meta, identifier=sender):
                raise ValueError('save meta error: %s, %s' % (sender, meta))

        # 1. verify and decrypt
        i_msg = super().verify_decrypt(msg)

        # 2. check: top-secret message
        if i_msg.content.type == ContentType.Forward:
            # do it again to drop the wrapper,
            # the secret inside the content is the real message
            content: ForwardContent = i_msg.content
            r_msg = content.forward
            secret = self.verify_decrypt(msg=r_msg)
            if secret is not None:
                return secret
            # FIXME: not for you?

        # OK
        return i_msg

    #
    #  ITransceiverDelegate
    #
    def send_package(self, data: bytes, handler: ICompletionHandler) -> bool:
        pass

    def upload_data(self, data: bytes, msg: InstantMessage) -> str:
        pass

    def download_data(self, url: str, msg: InstantMessage) -> bytes:
        pass
