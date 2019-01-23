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

from station.utils import json_str, json_dict
from station.config import station, session_server, database


class DIMRequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # remote user ID
        self.identifier = None

    def setup(self):
        print(self, 'set up with', self.client_address)

    def receive(self) -> list:
        data = b''
        while True:
            part = self.request.recv(1024)
            data += part
            if len(part) < 1024:
                break
        # split message(s)
        messages = []
        if len(data) > 0:
            array = data.decode('utf-8').splitlines()
            for line in array:
                msg = json_dict(line)
                msg = dimp.ReliableMessage(msg)
                messages.append(msg)
        return messages

    def send(self, msg: dimp.ReliableMessage):
        self.request.sendall(json_str(msg).encode('utf-8'))

    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)

        while True:
            messages = self.receive()
            if len(messages) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break
            for r_msg in messages:
                sender = r_msg.envelope.sender
                receiver = r_msg.envelope.receiver
                # check session
                if receiver == station.identifier:
                    # process message
                    print('*** message from client (%s:%s)...' % self.client_address)
                    content = station.unpack(msg=r_msg)
                    print('    content: %s' % content)
                    response = self.process(sender=sender, content=content)
                elif not session_server.valid(sender, self):
                    # handshake
                    print('*** handshake with client (%s:%s)...' % self.client_address)
                    response = self.handshake(sender=sender)
                else:
                    # save message for other users
                    print('@@@ message from "%s" to "%s"...' % (sender, receiver))
                    response = self.save(msg=r_msg)
                # pack and response
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s' % response)
                    msg = station.pack(receiver=sender, content=response)
                    self.send(msg=msg)

    def process(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        if content.type == dimp.MessageType.Command:
            if content['command'] == 'handshake':
                return self.handshake(sender=sender, content=content)
            else:
                print('Unknown command: ', content)
        else:
            # response client with the same message
            return content

    def handshake(self, sender: dimp.ID, content: dimp.Content=None) -> dimp.Content:
        if content and 'session' in content:
            session = content['session']
        else:
            session = None
        current = session_server.session(identifier=sender)
        if session == current.session_key:
            # session verified
            print('connect current request to session', sender, self.client_address)
            self.identifier = sender
            current.request = self
            return dimp.handshake_success_command()
        else:
            return dimp.handshake_again_command(session=current.session_key)

    def save(self, msg: dimp.ReliableMessage) -> dimp.Content:
        print('message to: %s' % msg.envelope.receiver)
        database.store_message(msg=msg)
        content = dimp.CommandContent.new(command='response')
        content['message'] = 'Sent OK!'
        return content

    def finish(self):
        if self.identifier:
            print('disconnect current request from session', self.identifier, self.client_address)
            current = session_server.session(identifier=self.identifier)
            current.request = None
        print(self, 'finish')
