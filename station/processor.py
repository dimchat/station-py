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
    Message Processor
    ~~~~~~~~~~~~~~~~~

    Message processor for Request Handler
"""

from dimp import ID, Meta
from dimp import ContentType, Content, TextContent, Command
from dimp import ReliableMessage
from dimp import HandshakeCommand, ProfileCommand, MetaCommand, ReceiptCommand

from common import g_facebook, g_database, Log
from common import s001

from .session import Session

from .config import g_session_server, g_dispatcher, g_receptionist, g_monitor


class MessageProcessor:

    def __init__(self, request_handler):
        super().__init__()
        self.request_handler = request_handler

    @property
    def client_address(self) -> str:
        return self.request_handler.client_address

    @property
    def identifier(self) -> ID:
        return self.request_handler.identifier

    def current_session(self, identifier: ID=None) -> Session:
        return self.request_handler.current_session(identifier=identifier)

    """
        main entrance
    """
    def process(self, msg: ReliableMessage) -> Content:
        # verify signature
        s_msg = current_station.verify_message(msg)
        if s_msg is None:
            Log.info('MessageProcessor: message verify error %s' % msg)
            response = TextContent.new(text='Signature error')
            response['signature'] = msg.signature
            return response
        # check receiver & session
        sender = g_facebook.identifier(s_msg.envelope.sender)
        receiver = g_facebook.identifier(s_msg.envelope.receiver)
        if receiver == current_station.identifier:
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            content = current_station.decrypt_message(s_msg)
            if content.type == ContentType.Command:
                Log.info('MessageProcessor: command from client %s, %s' % (self.client_address, content))
                return self.process_command(sender=sender, content=content)
            # talk with station?
            Log.info('MessageProcessor: message from client %s, %s' % (self.client_address, content))
            return self.process_dialog(sender=sender, content=content)
        # check session valid
        session = self.current_session(identifier=sender)
        if not session.valid:
            # session invalid, handshake first
            # NOTICE: if the client try to send message to another user before handshake,
            #         the message will be lost!
            return self.process_handshake(sender)
        # deliver message for receiver
        Log.info('MessageProcessor: delivering message %s' % msg.envelope)
        return self.deliver_message(msg)

    def process_dialog(self, sender: ID, content: Content) -> Content:
        Log.info('@@@ call NLP and response to the client %s, %s' % (self.client_address, sender))
        # TEST: response client with the same message here
        return content

    def process_command(self, sender: ID, content: Content) -> Content:
        command = content['command']
        if 'handshake' == command:
            # handshake protocol
            return self.process_handshake(sender=sender, cmd=HandshakeCommand(content))
        elif 'meta' == command:
            # meta protocol
            return self.process_meta_command(cmd=MetaCommand(content))
        elif 'profile' == command:
            # profile protocol
            return self.process_profile_command(cmd=ProfileCommand(content))
        elif 'users' == command:
            # show online users (connected)
            return self.process_users_command()
        elif 'search' == command:
            # search users with keyword(s)
            return self.process_search_command(cmd=Command(content))
        elif 'broadcast' == command:
            session = self.current_session(identifier=sender)
            if not session.valid:
                # session invalid, handshake first
                return self.process_handshake(sender)
            # broadcast
            return self.process_broadcast_command(cmd=Command(content))
        else:
            Log.info('MessageProcessor: unknown command %s' % content)

    def process_handshake(self, sender: ID, cmd: HandshakeCommand=None) -> Content:
        # set/update session in session server with new session key
        Log.info('MessageProcessor: handshake with client %s, %s' % (self.client_address, sender))
        if cmd is None:
            session_key = None
        else:
            session_key = cmd.session
        session = self.current_session(identifier=sender)
        if session_key == session.session_key:
            # session verified success
            session.valid = True
            session.active = True
            nickname = g_facebook.nickname(identifier=sender)
            cli = self.client_address
            Log.info('MessageProcessor: handshake accepted %s %s %s, %s' % (nickname, cli, sender, session_key))
            g_monitor.report(message='User %s logged in %s %s' % (nickname, cli, sender))
            # add the new guest for checking offline messages
            g_receptionist.add_guest(identifier=sender)
            return HandshakeCommand.success()
        else:
            # session key not match, ask client to sign it with the new session key
            return HandshakeCommand.again(session=session.session_key)

    def process_meta_command(self, cmd: MetaCommand) -> Content:
        identifier = cmd.identifier
        meta = cmd.meta
        if meta:
            # received a meta for ID
            meta = Meta(meta)
            Log.info('MessageProcessor: received meta %s' % identifier)
            if g_database.save_meta(identifier=identifier, meta=meta):
                # meta saved
                return ReceiptCommand.receipt(message='Meta for %s received!' % identifier)
            else:
                # meta not match
                return TextContent.new(text='Meta not match %s!' % identifier)
        else:
            # querying meta for ID
            Log.info('MessageProcessor: search meta %s' % identifier)
            meta = g_database.meta(identifier=identifier)
            if meta:
                return MetaCommand.response(identifier=identifier, meta=meta)
            else:
                return TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    def process_profile_command(self, cmd: ProfileCommand) -> Content:
        identifier = cmd.identifier
        meta = cmd.meta
        if meta is not None:
            if g_database.save_meta(identifier=identifier, meta=meta):
                # meta saved
                Log.info('MessageProcessor: meta cached %s, %s' % (identifier, meta))
            else:
                Log.info('MessageProcessor: meta not match %s, %s' % (identifier, meta))
        profile = cmd.profile
        if profile is not None:
            # received a new profile for ID
            Log.info('MessageProcessor: received profile %s' % identifier)
            if g_database.save_profile(profile=profile):
                # profile saved
                return ReceiptCommand.receipt(message='Profile of %s received!' % identifier)
            else:
                # signature not match
                return TextContent.new(text='Profile signature not match %s!' % identifier)
        else:
            # querying profile for ID
            Log.info('MessageProcessor: search profile %s' % identifier)
            profile = g_database.profile(identifier=identifier)
            if profile is not None:
                return ProfileCommand.response(identifier=identifier, profile=profile)
            else:
                return TextContent.new(text='Sorry, profile for %s not found.' % identifier)

    def process_users_command(self) -> Content:
        Log.info('MessageProcessor: get online user(s) for %s' % self.identifier)
        users = g_session_server.random_users(max_count=20)
        response = Command.new(command='users')
        response['message'] = '%d user(s) connected' % len(users)
        response['users'] = users
        return response

    def process_search_command(self, cmd: Command) -> Content:
        Log.info('MessageProcessor: search users for %s, %s' % (self.identifier, cmd))
        # keywords
        keywords = cmd.get('keywords')
        if keywords is None:
            keywords = cmd.get('keyword')
            if keywords is None:
                keywords = cmd.get('kw')
        # search for each keyword
        if keywords is None:
            keywords = []
        else:
            keywords = keywords.split(' ')
        results = g_database.search(keywords=keywords)
        # response
        users = list(results.keys())
        response = Command.new(command='search')
        response['message'] = '%d user(s) found' % len(users)
        response['users'] = users
        response['results'] = results
        return response

    def process_broadcast_command(self, cmd: Command) -> Content:
        Log.info('MessageProcessor: client broadcast %s, %s' % (self.identifier, cmd))
        title = cmd.get('title')
        if 'report' == title:
            # report client state
            state = cmd.get('state')
            Log.info('MessageProcessor: client report state %s' % state)
            if state is not None:
                session = self.current_session()
                if 'background' == state:
                    session.active = False
                elif 'foreground' == state:
                    # welcome back!
                    g_receptionist.add_guest(identifier=session.identifier)
                    session.active = True
                else:
                    Log.info('MessageProcessor: unknown state %s' % state)
                    session.active = True
                return ReceiptCommand.receipt(message='Client state received')
        elif 'apns' == title:
            # submit device token for APNs
            token = cmd.get('device_token')
            Log.info('MessageProcessor: client report token %s' % token)
            if token is not None:
                g_database.save_device_token(token=token, identifier=self.identifier)
                return ReceiptCommand.receipt(message='Token received')
        else:
            Log.info('MessageProcessor: unknown broadcast command %s' % cmd)

    def deliver_message(self, msg: ReliableMessage) -> Content:
        Log.info('MessageProcessor: deliver message %s, %s' % (self.identifier, msg.envelope))
        g_dispatcher.deliver(msg)
        # response to sender
        response = ReceiptCommand.receipt(message='Message delivering')
        # extra info
        sender = msg.get('sender')
        receiver = msg.get('receiver')
        time = msg.get('time')
        group = msg.get('group')
        signature = msg.get('signature')
        # envelope
        response['sender'] = sender
        response['receiver'] = receiver
        if time is not None:
            response['time'] = time
        # group message?
        if group is not None and group != receiver:
            response['group'] = group
        # signature
        response['signature'] = signature
        return response


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
current_station = s001
