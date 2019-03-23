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

    @property
    def client_address(self) -> str:
        return self.request_handler.client_address

    @property
    def identifier(self) -> dimp.ID:
        return self.request_handler.identifier

    def session_valid(self, identifier: dimp.ID) -> bool:
        return self.request_handler.session_valid(identifier=identifier)

    def clear_session(self):
        self.request_handler.clear_session()

    def reset_session(self, identifier: dimp.ID, session_key: str) -> Session:
        return self.request_handler.reset_session(identifier=identifier, session_key=session_key)

    """
        main entrance
    """
    def process(self, msg: dimp.ReliableMessage) -> dimp.Content:
        # verify signature
        s_msg = station.verify(msg)
        if s_msg is None:
            print('!!! message verify error: %s' % msg)
            response = dimp.TextContent.new(text='Signature error')
            response['signature'] = msg.signature
            return response
        # check receiver & session
        sender = dimp.ID(s_msg.envelope.sender)
        receiver = dimp.ID(s_msg.envelope.receiver)
        if receiver == station.identifier:
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            content = station.decrypt(s_msg)
            if content.type == dimp.MessageType.Command:
                print('*** command from client (%s:%s)...' % self.client_address)
                print('    content: %s' % content)
                return self.process_command(sender=sender, content=content)
            else:
                # TEST: response client with the same message
                print('*** message from client (%s:%s)...' % self.client_address)
                print('    content: %s' % content)
                return content
        elif not self.session_valid(identifier=sender):
            # session invalid, handshake first
            #    NOTICE: if the client try to send message to another user before handshake,
            #            the message will be lost!
            print('*** handshake with client (%s:%s)...' % self.client_address)
            return self.process_handshake_command(sender)
        else:
            # save(deliver) message for other users
            print('@@@ message deliver from "%s" to "%s"...' % (sender, receiver))
            return self.deliver_message(msg)

    def process_command(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        command = content['command']
        if 'handshake' == command:
            # handshake protocol
            return self.process_handshake_command(sender, content=content)
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
            # post device token
            return self.process_apns_command(content=content)
        else:
            print('Unknown command: ', content)

    def process_handshake_command(self, identifier: dimp.ID, content: dimp.Content=None) -> dimp.Content:
        # 1. clear current session
        self.clear_session()
        # 2. set/update session in session server with new session key
        if content and 'session' in content:
            session_key = content['session']
        else:
            session_key = None
        session = self.reset_session(identifier=identifier, session_key=session_key)
        if session.valid:
            # session verified success
            print('connect current request to session', identifier, self.client_address)
            # add the new guest for checking offline messages
            receptionist.add_guest(identifier=identifier)
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
            print('received meta for %s from %s ...' % (identifier, self.identifier))
            if database.cache_meta(identifier=identifier, meta=meta):
                # meta saved
                response = dimp.CommandContent.new(command='receipt')
                response['message'] = 'Meta for %s received!' % identifier
                return response
            else:
                # meta not match
                return dimp.TextContent.new(text='Meta not match %s!' % identifier)
        else:
            # querying meta for ID
            print('search meta of %s for %s ...' % (identifier, self.identifier))
            meta = database.meta(identifier=identifier)
            if meta:
                return dimp.MetaCommand.response(identifier=identifier, meta=meta)
            else:
                return dimp.TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    def process_profile_command(self, content: dimp.Content) -> dimp.Content:
        identifier = dimp.ID(content['ID'])
        if 'meta' in content:
            meta = content['meta']
            meta = dimp.Meta(meta)
            print('received meta for %s from %s ...' % (identifier, self.identifier))
            if database.cache_meta(identifier=identifier, meta=meta):
                # meta saved
                print('meta saved for %s.' % identifier)
            else:
                print('meta not match %s!' % identifier)
        if 'profile' in content:
            # received a new profile for ID
            print('received profile for %s from %s ...' % (identifier, self.identifier))
            profile = content['profile']
            signature = content['signature']
            if database.save_profile_signature(identifier=identifier, profile=profile, signature=signature):
                # profile saved
                response = dimp.CommandContent.new(command='receipt')
                response['message'] = 'Profile for %s received!' % identifier
                return response
            else:
                # signature not match
                return dimp.TextContent.new(text='Profile signature not match %s!' % identifier)
        else:
            # querying profile for ID
            print('search profile of %s for %s ...' % (identifier, self.identifier))
            info = database.profile(identifier=identifier)
            if info:
                prf = info['profile']
                sig = info['signature']
                return dimp.ProfileCommand.response(identifier=identifier, profile=prf, signature=sig)
            else:
                return dimp.TextContent.new(text='Sorry, profile for %s not found.' % identifier)

    def process_users_command(self) -> dimp.Content:
        print('get online user(s) for %s ...' % self.identifier)
        sessions = session_server.valid_sessions()
        users = [sess.identifier for sess in sessions]
        response = dimp.CommandContent.new(command='users')
        response['message'] = '%d user(s) connected' % len(users)
        response['users'] = users
        return response

    def process_search_command(self, content: dimp.Content) -> dimp.Content:
        print('search for %s ...' % self.identifier)
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
        results = database.search(keywords=keywords)
        # response
        users = list(results.keys())
        response = dimp.CommandContent.new(command='search')
        response['message'] = '%d user(s) found' % len(users)
        response['users'] = users
        response['results'] = results
        return response

    def process_apns_command(self, content: dimp.Content) -> dimp.Content:
        identifier = content.get('ID')
        token = content.get('device_token')
        if identifier and token:
            database.cache_device_token(identifier=identifier, token=token)
            response = dimp.CommandContent.new(command='receipt')
            response['message'] = 'Token received'
            response['device_token'] = token
            return response

    def deliver_message(self, msg: dimp.ReliableMessage) -> dimp.Content:
        print('%s send message from %s to %s' % (self.identifier, msg.envelope.sender, msg.envelope.receiver))
        dispatcher.deliver(msg)
        # response to sender
        response = dimp.CommandContent.new(command='receipt')
        response['message'] = 'Message delivering'
        response['signature'] = msg['signature']
        return response
