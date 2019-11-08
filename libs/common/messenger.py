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

from typing import Optional

from dimp import ID, User
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import Content, ForwardContent, TextContent
from dimsdk import Session, SessionServer, ReceiptCommand
from dimsdk import Messenger as Transceiver
from dimsdk import ContentProcessor


class Messenger(Transceiver):

    def __init__(self):
        super().__init__()

    @property
    def dispatcher(self):
        return self.context['dispatcher']

    #
    #   Session with ID, (IP, port), session key, valid
    #
    def current_session(self, identifier: ID=None) -> Optional[Session]:
        session: Session = self.context.get('session')
        if identifier is None:
            # get current session
            return session
        if session is not None:
            # check whether the current session's identifier matched
            if session.identifier == identifier:
                # current session belongs to the same user
                return session
            else:
                # user switched, clear current session
                self.session_server.remove(session=session)
        # get new session with identifier
        session = self.session_server.new(identifier=identifier, client_address=self.remote_address)
        self.context['session'] = session
        return session

    def clear_session(self):
        session: Session = self.context.get('session')
        if session is not None:
            self.session_server.remove(session=session)
            self.context.pop('session')

    @property
    def session_server(self) -> SessionServer:
        return self.context.get('session_server')

    #
    #   Remote user(for station) or station(for client)
    #
    @property
    def remote_user(self) -> User:
        return self.context.get('remote_user')

    @remote_user.setter
    def remote_user(self, value: User):
        if value is None:
            self.context.pop('remote_user', None)
        else:
            self.context['remote_user'] = value

    @property
    def remote_address(self):  # (IP, port)
        return self.context.get('remote_address')

    # @remote_address.setter
    # def remote_address(self, value):
    #     if value is None:
    #         self.context.pop('remote_address', None)
    #     else:
    #         self.context['remote_address'] = value

    @property
    def current_user(self) -> Optional[User]:
        return super().current_user

    @current_user.setter
    def current_user(self, value: User):
        users = self.local_users
        if value in users:
            self.__alter(current_user=value)
        else:
            users.insert(0, value)

    def __alter(self, current_user: User):
        """ Alter the position of this user to the front """
        local_users = self.local_users
        for index, user in enumerate(local_users):
            if user.identifier == current_user.identifier:
                # got it
                if index > 0:
                    # move this user in front for next message
                    item = local_users.pop(index)
                    assert item == current_user, 'should not happen'
                    local_users.insert(0, current_user)
                # done!
                break

    def __select(self, receiver: ID=None, group: ID=None) -> Optional[User]:
        """ Select a local user for decrypting message """
        local_users = self.local_users
        if receiver is None:
            # group message (recipient not designated)
            assert group.type.is_group(), 'group ID error: %s' % group
            if group.is_broadcast:
                return self.current_user
            members = self.facebook.members(identifier=group)
            if members is None:
                # TODO: query group members
                return None
            # check which local user is in the group's member-list
            for user in local_users:
                if user.identifier in members:
                    # got it
                    self.__alter(current_user=user)
                    return user
            # FIXME: not for you?
        else:
            # 1. personal message
            # 2. split group message
            assert receiver.type.is_user(), 'receiver ID error: %s' % receiver
            if receiver.is_broadcast:
                return self.current_user
            for user in local_users:
                if user.identifier == receiver:
                    # got it
                    self.__alter(current_user=user)
                    return user

    #
    #   super()
    #
    def cpu(self, context: dict=None) -> ContentProcessor:
        assert context is None, 'use messenger.context only'
        return super().cpu(context=self.context)

    def send_content(self, content: Content, receiver: ID) -> bool:
        sender = self.current_user.identifier
        msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        return self.send_message(msg=msg)

    def deliver_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        # call dispatcher to deliver this message
        response = self.dispatcher.deliver(msg=msg)
        if response is None:
            return None
        # response
        sender = self.current_user.identifier
        receiver = self.barrack.identifier(msg.envelope.sender)
        msg = InstantMessage.new(content=response, sender=sender, receiver=receiver)
        return self.encrypt_sign(msg=msg)

    def forward_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = self.barrack.identifier(msg.envelope.receiver)
        contact = self.facebook.user(identifier=receiver)
        cmd = ForwardContent.new(message=msg)
        if self.send_content(content=cmd, receiver=receiver):
            text = 'Top-secret message forwarded: %s' % contact.name
            response = ReceiptCommand.new(message=text)
        else:
            text = 'Top-secret message not forwarded: %s' % contact.name
            response = TextContent.new(text=text)
        # response
        sender = self.current_user.identifier
        msg = InstantMessage.new(content=response, sender=sender, receiver=receiver)
        return self.encrypt_sign(msg=msg)

    #
    #   Transform
    #
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if msg.meta is None:
            sender = self.facebook.identifier(msg.envelope.sender)
            meta = self.facebook.meta(identifier=sender)
            if meta is None:
                # TODO: keep this message in waiting list for meta response
                return None
        return super().verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        receiver = self.barrack.identifier(msg.envelope.receiver)
        if receiver.type.is_user():
            # check whether the receiver is in local users
            user = self.__select(receiver=receiver)
            if user is not None:
                return super().decrypt_message(msg=msg)
        elif receiver.type.is_group():
            # check which local user is in the group's member-list
            user = self.__select(group=receiver)
            if user is not None:
                # trim it
                msg = msg.trim(member=user.identifier)
                return super().decrypt_message(msg=msg)
