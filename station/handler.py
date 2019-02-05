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
from .config import station, session_server
from .processor import MessageProcessor


class RequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # message processor
        self.processor = None
        # remote user ID
        self.identifier = None
        # received data (maybe sent partially)
        self.received_data = None

    def setup(self):
        print(self, 'set up with', self.client_address)
        self.processor = MessageProcessor(handler=self)
        self.identifier = None
        self.received_data = None

    def finish(self):
        if self.identifier:
            print('disconnect current request from session', self.identifier, self.client_address)
            response = dimp.TextContent.new(text='Bye!')
            msg = station.pack(receiver=self.identifier, content=response)
            self.send_message(msg)
            current = session_server.session(identifier=self.identifier)
            current.request_handler = None
        if self.received_data is not None:
            print('!!! incomplete data:', self.received_data.decode('utf-8'))
        print(self, 'finish')

    """
        main entrance
    """
    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)

        while station.running:
            # receive and unwrap messages
            messages = self.receive()
            if len(messages) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break
            for msg in messages:
                # data error
                if 'error' in msg:
                    print('received:', msg)
                    data = msg['data'].encode('utf-8')
                    self.request.sendall(data)
                    continue
                # process one message
                response = self.processor.process(msg)
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s' % response)
                    msg = station.pack(receiver=msg.envelope.sender, content=response)
                    self.send_message(msg)

    def receive(self) -> list:
        # check the incomplete data
        if self.received_data is None:
            self.received_data = b''
        while True:
            part = self.request.recv(1024)
            self.received_data += part
            if len(part) < 1024:
                break
        # unwrap
        try:
            data = self.received_data.decode('utf-8')
            self.received_data = None
            # if the message data was wrap by other transfer protocol,
            # unwrap here
        except UnicodeDecodeError as error:
            print('decode error:', self.received_data)
            return [{'data': self.received_data, 'error': error}]
        # split messages (one line one message)
        messages = []
        lines = data.splitlines()
        index = 0
        for line in lines:
            index += 1
            try:
                msg = dimp.ReliableMessage(json_dict(line))
                messages.append(msg)
            except ValueError as error:
                if index == lines.count:
                    # partially data, push back for next input
                    self.received_data = line.encode('utf-8')
                else:
                    print('value error:', line)
                    messages.append({'data': line, 'error': error})
        return messages

    def send_message(self, msg: dimp.ReliableMessage):
        data = json_str(msg) + '\n'
        data = data.encode('utf-8')
        self.request.sendall(data)
