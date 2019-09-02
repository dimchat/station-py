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
import json

from dimp import Meta
from dimp import InstantMessage, ReliableMessage, ContentType, ForwardContent
from dimp import Transceiver, ICompletionHandler, ICallback
from dkd import SecureMessage

from .facebook import Facebook


class Messenger(Transceiver):

    def __init__(self):
        super().__init__()

    #
    #  Transform
    #
    def verify_message(self, msg: ReliableMessage):
        # [Meta Protocol] check meta in first contact message
        sender = self.barrack.identifier(msg.envelope.sender)
        meta = self.barrack.meta(identifier=sender)
        if meta is None:
            # first contact, try meta in message package
            meta = Meta(msg.meta)
            if meta is None:
                # TODO: query meta for sender from DIM network
                #       (do it by application)
                return None
            elif not meta.match_identifier(sender):
                raise ValueError('meta not match: %s, %s' % (sender, meta))
            # save meta for new contact
            facebook: Facebook = self.barrack
            if not facebook.save_meta(meta=meta, identifier=sender):
                raise RuntimeError('save meta error: %s, %s' % (sender, meta))
        return super().verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage):
        i_msg = super().decrypt_message(msg=msg)
        # check: top-secret message
        if i_msg.content.type == ContentType.Forward:
            # do it again to drop the wrapper,
            # the secret inside the content is the real message
            content: ForwardContent = i_msg.content
            r_msg = content.forward
            secret = self.verify_decrypt(msg=r_msg)
            if secret is not None:
                return secret
            # FIXME: not for you?
        return i_msg

    #
    #  Conveniences
    #
    def encrypt_sign(self, msg: InstantMessage) -> ReliableMessage:
        # 1. encrypt 'content' to 'data' for receiver
        s_msg = self.encrypt_message(msg=msg)
        # 2. sign 'data' by sender
        r_msg = self.sign_message(msg=s_msg)
        # OK
        return r_msg

    def verify_decrypt(self, msg: ReliableMessage) -> InstantMessage:
        # 1. verify 'data' with 'signature'
        s_msg = self.verify_message(msg=msg)
        # 2. check group message
        receiver = self.barrack.identifier(msg.envelope.receiver)
        if receiver.type.is_group():
            # TODO: split it
            pass
        # 3. decrypt 'data' to 'content'
        i_msg = self.decrypt_message(msg=s_msg)
        # OK
        return i_msg

    #
    #   Send message
    #
    def send_message(self, msg: InstantMessage, callback: ICallback, split: bool) -> bool:
        """
        Send message (secured + certified) to target station

        :param msg:      instant message
        :param callback: callback function
        :param split:    if it's a group message, split it before sending out
        :return:         False on data/delegate error
        """
        # transforming
        r_msg = self.encrypt_sign(msg=msg)
        if r_msg is None:
            raise AssertionError('failed to encrypt and sign message: %s' % msg)
        # trying to send out
        ok = True
        receiver = self.barrack.identifier(msg.envelope.receiver)
        if split and receiver.type.is_group():
            group = self.barrack.group(identifier=receiver)
            if group is None:
                raise LookupError('failed to create group: %s' % receiver)
            messages = r_msg.split(members=group.members)
            if messages is None:
                # failed to split msg, send it to group
                ok = self.__send_message(msg=r_msg, callback=callback)
            else:
                # sending group message one by one
                for r_msg in messages:
                    if not self.__send_message(msg=r_msg, callback=callback):
                        ok = False
        else:
            ok = self.__send_message(msg=r_msg, callback=callback)
        # TODO: if OK, set iMsg.state = sending; else set iMsg.state = waiting
        return ok

    def __send_message(self, msg: ReliableMessage, callback: ICallback) -> bool:
        data = json.dumps(msg).encode('utf-8')
        handler = CompletionHandler(msg=msg, cb=callback)
        assert self.delegate is not None, 'messenger delegate not set yet'
        return self.delegate.send_package(data=data, handler=handler)


class CompletionHandler(ICompletionHandler):

    def __init__(self, msg: ReliableMessage, cb: ICallback):
        super().__init__()
        self.msg = msg
        self.callback = cb

    def success(self):
        self.callback.finished(result=self.msg, error=None)

    def failed(self, error):
        self.callback.finished(result=self.msg, error=error)
