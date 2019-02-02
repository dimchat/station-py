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

from socketserver import BaseRequestHandler

import dimp

from .utils import json_str, json_dict
from .config import station, session_server, database


class RequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # remote user ID
        self.identifier = None

    def setup(self):
        print(self, 'set up with', self.client_address)
        self.identifier = None

    def receive(self) -> list:
        data = b''
        while True:
            part = self.request.recv(1024)
            data += part
            if len(part) < 1024:
                break
        # split message(s)
        messages = []
        try:
            data = data.decode('utf-8')
        except UnicodeDecodeError as error:
            print('decode error:', data)
            messages.append({'data': data, 'error': error})
            return messages
        # one line one message
        lines = data.splitlines()
        for line in lines:
            try:
                msg = dimp.ReliableMessage(json_dict(line))
            except ValueError as error:
                print('value error:', line)
                messages.append({'data': line, 'error': error})
                continue
            messages.append(msg)
        return messages

    def send(self, msg: dimp.ReliableMessage):
        data = json_str(msg) + '\n'
        data = data.encode('utf-8')
        self.request.sendall(data)

    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)

        while station.running:
            messages = self.receive()
            if len(messages) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break
            for r_msg in messages:
                if 'error' in r_msg:
                    self.process_raw_data(r_msg)
                    continue
                # unpack
                s_msg = station.verify(r_msg)
                if s_msg is None:
                    print('!!! message verify error: %s' % r_msg)
                    continue
                sender = s_msg.envelope.sender
                receiver = s_msg.envelope.receiver
                # check session
                if receiver == station.identifier:
                    # process message (handshake first)
                    content = station.decrypt(s_msg)
                    print('*** message from client (%s:%s)...' % self.client_address)
                    print('    content: %s' % content)
                    response = self.process(sender=sender, content=content)
                elif not session_server.valid(sender, self):
                    # handshake
                    print('*** handshake with client (%s:%s)...' % self.client_address)
                    response = self.process_handshake_command(sender)
                else:
                    # save message for other users
                    print('@@@ message from "%s" to "%s"...' % (sender, receiver))
                    response = self.save(r_msg)
                # pack and response
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s' % response)
                    msg = station.pack(receiver=sender, content=response)
                    self.send(msg)

    def process_raw_data(self, info: dict):
        print('received:', info)
        data = info['data']
        # data = data.encode('utf-8')
        self.request.sendall(data)

    def process(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        if content.type == dimp.MessageType.Command:
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
            else:
                print('Unknown command: ', content)
        else:
            # response client with the same message
            return content

    def process_handshake_command(self, identifier: dimp.ID, content: dimp.Content=None) -> dimp.Content:
        if content and 'session' in content:
            session_key = content['session']
        else:
            session_key = None
        current = session_server.session(identifier=identifier)
        if session_key == current.session_key:
            # session verified
            print('connect current request to session', identifier, self.client_address)
            self.identifier = identifier
            current.request_handler = self
            return dimp.HandshakeCommand.success()
        else:
            return dimp.HandshakeCommand.again(session=current.session_key)

    def process_meta_command(self, content: dimp.Content) -> dimp.Content:
        cmd = dimp.MetaCommand(content)
        identifier = cmd.identifier
        meta = cmd.meta
        if meta:
            # received a meta for ID
            print('received meta for %s from %s ...' % (identifier, self.identifier))
            if database.save_meta(identifier=identifier, meta=meta):
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
            meta = database.load_meta(identifier=identifier)
            if meta:
                return dimp.MetaCommand.response(identifier=identifier, meta=meta)
            else:
                return dimp.TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    def process_profile_command(self, content: dimp.Content) -> dimp.Content:
        identifier = dimp.ID(content['ID'])
        if 'profile' in content:
            # received a new profile for ID
            print('received profile for %s from %s ...' % (identifier, self.identifier))
            profile = content['profile']
            signature = content['signature']
            if database.save_profile(identifier=identifier, profile=profile, signature=signature):
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
            info = database.load_profile(identifier=identifier)
            if info:
                prf = info['profile']
                sig = info['signature']
                return dimp.ProfileCommand.response(identifier=identifier, profile=prf, signature=sig)
            else:
                return dimp.TextContent.new(text='Sorry, profile for %s not found.' % identifier)

    def process_users_command(self) -> dimp.Content:
        print('get online user(s) for %s ...' % self.identifier)
        sessions = session_server.sessions.copy()
        users = [identifier for identifier in sessions if sessions[identifier].request_handler]
        response = dimp.CommandContent.new(command='users')
        response['message'] = '%d user(s) connected' % len(users)
        response['users'] = users
        return response

    def process_search_command(self, content: dimp.Content) -> dimp.Content:
        print('search for %s ...' % self.identifier)
        identifier = None
        number = 0
        # keywords
        if 'keywords' in content:
            keyword = content['keywords']
            # only the first keyword
            keyword = keyword.split(',')[0]
            keyword = keyword.split(' ')[0]
        elif 'keyword' in content:
            keyword = content['keyword']
        elif 'kw' in content:
            keyword = content['kw']
        else:
            keyword = None
        # get ID/number from keywords
        if keyword:
            if keyword.find('@') > 0:
                identifier = dimp.ID(keyword)
            else:
                keyword = keyword.replace('-', '')
                number = int(keyword)
        elif 'ID' in content:
            identifier = dimp.ID(content['ID'])
        elif 'number' in content:
            number = content['number']
            number = number.replace('-', '')
            number = int(number)
        # search results
        users = []
        results = {}
        if identifier:
            meta = database.load_meta(identifier=identifier)
            if meta:
                users.append(identifier)
                results[identifier] = meta
        elif number > 0:
            results = database.search(number=number)
            users = list(results.keys())
        response = dimp.CommandContent.new(command='search')
        response['users'] = users
        response['results'] = results
        return response

    def save(self, msg: dimp.ReliableMessage) -> dimp.Content:
        print('%s sent message from %s to %s' % (self.identifier, msg.envelope.sender, msg.envelope.receiver))
        database.store_message(msg)
        response = dimp.CommandContent.new(command='receipt')
        response['message'] = 'Message received!'
        return response

    def finish(self):
        if self.identifier:
            print('disconnect current request from session', self.identifier, self.client_address)
            response = dimp.TextContent.new(text='Bye!')
            msg = station.pack(receiver=self.identifier, content=response)
            self.send(msg)
            current = session_server.session(identifier=self.identifier)
            current.request_handler = None
        print(self, 'finish')
