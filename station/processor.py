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
import dimp

from .session import Session
from .config import station, session_server, database, dispatcher, receptionist


class MessageProcessor:

    def __init__(self, request_handler):
        super().__init__()
        self.request_handler = request_handler
        self.station = station
        self.session_server = session_server
        self.database = database
        self.dispatcher = dispatcher
        self.receptionist = receptionist

    @property
    def client_address(self) -> str:
        return self.request_handler.client_address

    @property
    def identifier(self) -> dimp.ID:
        return self.request_handler.identifier

    def current_session(self, identifier: dimp.ID=None) -> Session:
        return self.request_handler.current_session(identifier=identifier)

    """
        main entrance
    """
    def process(self, msg: dimp.ReliableMessage) -> dimp.Content:
        # verify signature
        s_msg = self.station.verify(msg)
        if s_msg is None:
            print('MessageProcessor: message verify error', msg)
            response = dimp.TextContent.new(text='Signature error')
            response['signature'] = msg.signature
            return response
        # check receiver & session
        sender = dimp.ID(s_msg.envelope.sender)
        receiver = dimp.ID(s_msg.envelope.receiver)
        if receiver == self.station.identifier:
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            content = self.station.decrypt(s_msg)
            if content.type == dimp.MessageType.Command:
                print('MessageProcessor: command from client', self.client_address, content)
                return self.process_command(sender=sender, content=content)
            # talk with station?
            print('MessageProcessor: message from client', self.client_address, content)
            return self.process_dialog(sender=sender, content=content)
        # check session valid
        session = self.current_session(identifier=sender)
        if not session.valid:
            # session invalid, handshake first
            # NOTICE: if the client try to send message to another user before handshake,
            #         the message will be lost!
            return self.process_handshake_command(sender)
        # deliver message for receiver
        print('MessageProcessor: delivering message with envelope', msg.envelope)
        return self.deliver_message(msg)

    def process_dialog(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        print('@@@ call NLP and response to the client', self.client_address, sender)
        # TEST: response client with the same message here
        return content

    def process_command(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        command = content['command']
        if 'handshake' == command:
            # handshake protocol
            return self.process_handshake_command(sender=sender, content=content)
        elif 'meta' == command:
            # meta protocol
            return self.process_meta_command(content=content)
        elif 'profile' == command:
            # profile protocol
            return self.process_profile_command(content=content)
        elif 'users' == command:
            # show online users (connected)
            return self.process_users_command()
        elif 'search' == command:
            return self.process_search_command(content=content)
        elif 'apns' == command:
            session = self.current_session(identifier=sender)
            if not session.valid:
                # session invalid, handshake first
                return self.process_handshake_command(sender)
            # post device token
            return self.process_apns_command(content=content)
        elif 'report' == command:
            session = self.current_session(identifier=sender)
            if not session.valid:
                # session invalid, handshake first
                return self.process_handshake_command(sender)
            # report client status
            return self.process_report_command(content=content)
        else:
            print('MessageProcessor: unknown command', content)

    def process_handshake_command(self, sender: dimp.ID, content: dimp.Content=None) -> dimp.Content:
        # set/update session in session server with new session key
        print('MessageProcessor: handshake with client', self.client_address, sender)
        if content and 'session' in content:
            session_key = content['session']
        else:
            session_key = None
        session = self.current_session(identifier=sender)
        if session_key == session.session_key:
            # session verified success
            session.valid = True
            session.active = True
            print('MessageProcessor: handshake accepted', self.client_address, sender, session_key)
            # add the new guest for checking offline messages
            self.receptionist.add_guest(identifier=sender)
            return dimp.HandshakeCommand.success()
        else:
            # session key not match, ask client to sign it with the new session key
            return dimp.HandshakeCommand.again(session=session.session_key)

    def process_meta_command(self, content: dimp.Content) -> dimp.Content:
        cmd = dimp.MetaCommand(content)
        identifier = cmd.identifier
        meta = cmd.meta
        if meta:
            # received a meta for ID
            meta = dimp.Meta(meta)
            print('MessageProcessor: received meta', identifier, meta)
            if self.database.cache_meta(identifier=identifier, meta=meta):
                # meta saved
                response = dimp.CommandContent.new(command='receipt')
                response['message'] = 'Meta for %s received!' % identifier
                return response
            else:
                # meta not match
                return dimp.TextContent.new(text='Meta not match %s!' % identifier)
        else:
            # querying meta for ID
            print('MessageProcessor: search meta', identifier)
            meta = self.database.meta(identifier=identifier)
            if meta:
                return dimp.MetaCommand.response(identifier=identifier, meta=meta)
            else:
                return dimp.TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    def process_profile_command(self, content: dimp.Content) -> dimp.Content:
        identifier = dimp.ID(content['ID'])
        if 'meta' in content:
            meta = content['meta']
            meta = dimp.Meta(meta)
            print('MessageProcessor: received meta', identifier, meta)
            if self.database.cache_meta(identifier=identifier, meta=meta):
                # meta saved
                print('MessageProcessor: meta cached', identifier, meta)
            else:
                print('MessageProcessor: meta not match', identifier, meta)
        if 'profile' in content:
            # received a new profile for ID
            profile = content['profile']
            signature = content['signature']
            print('MessageProcessor: received profile', identifier, profile, signature)
            if self.database.save_profile_signature(identifier=identifier, profile=profile, signature=signature):
                # profile saved
                response = dimp.CommandContent.new(command='receipt')
                response['message'] = 'Profile of %s received!' % identifier
                return response
            else:
                # signature not match
                return dimp.TextContent.new(text='Profile signature not match %s!' % identifier)
        else:
            # querying profile for ID
            print('MessageProcessor: search profile', identifier)
            info = self.database.profile_signature(identifier=identifier)
            if info:
                prf = info['profile']
                sig = info['signature']
                return dimp.ProfileCommand.response(identifier=identifier, profile=prf, signature=sig)
            else:
                return dimp.TextContent.new(text='Sorry, profile for %s not found.' % identifier)

    def process_users_command(self) -> dimp.Content:
        print('MessageProcessor: get online user(s) for', self.identifier)
        users = self.session_server.random_users(max_count=20)
        response = dimp.CommandContent.new(command='users')
        response['message'] = '%d user(s) connected' % len(users)
        response['users'] = users
        return response

    def process_search_command(self, content: dimp.Content) -> dimp.Content:
        print('MessageProcessor: search users for', self.identifier, content)
        # keywords
        if 'keywords' in content:
            keywords = content['keywords']
        elif 'keyword' in content:
            keywords = content['keyword']
        elif 'kw' in content:
            keywords = content['kw']
        else:
            raise ValueError('keywords not found')
        # search for each keyword
        keywords = keywords.split(' ')
        results = self.database.search(keywords=keywords)
        # response
        users = list(results.keys())
        response = dimp.CommandContent.new(command='search')
        response['message'] = '%d user(s) found' % len(users)
        response['users'] = users
        response['results'] = results
        return response

    def process_apns_command(self, content: dimp.Content) -> dimp.Content:
        print('MessageProcessor: APNs device token', self.identifier, content)
        identifier = content.get('ID')
        token = content.get('device_token')
        if identifier and token:
            self.database.cache_device_token(identifier=identifier, token=token)
            response = dimp.CommandContent.new(command='receipt')
            response['message'] = 'Token received'
            response['device_token'] = token
            return response

    def process_report_command(self, content: dimp.Content) -> dimp.Content:
        print('MessageProcessor: client report', self.identifier, content)
        state = content.get('state')
        if state is not None:
            session = self.current_session()
            if 'background' == state:
                session.active = False
            else:
                session.active = True
            response = dimp.CommandContent.new(command='receipt')
            response['message'] = 'Client state for %s received!' % session.identifier
            return response
        else:
            print('MessageProcessor: unknown report command', content)

    def deliver_message(self, msg: dimp.ReliableMessage) -> dimp.Content:
        print('MessageProcessor: deliver message', self.identifier, msg.envelope)
        self.dispatcher.deliver(msg)
        # response to sender
        response = dimp.CommandContent.new(command='receipt')
        response['message'] = 'Message delivering'
        response['signature'] = msg['signature']
        return response
