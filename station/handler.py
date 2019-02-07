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

    def setup(self):
        print(self, 'set up with', self.client_address)
        self.processor = MessageProcessor(handler=self)
        self.identifier = None

    def finish(self):
        if self.identifier:
            print('disconnect current request from session', self.identifier, self.client_address)
            response = dimp.TextContent.new(text='Bye!')
            msg = station.pack(receiver=self.identifier, content=response)
            self.send_message(msg)
            current = session_server.session(identifier=self.identifier)
            current.request_handler = None
        print(self, 'finish', self.client_address)

    """
        DIM Request Handler
    """
    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)
        incomplete_data = None
        while station.running:
            # 1. receive all data
            data = b''
            while True:
                part = self.request.recv(1024)
                data += part
                if len(part) < 1024:
                    break
            if len(data) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break

            # 2. check incomplete data
            if incomplete_data is not None:
                data = incomplete_data + data
                incomplete_data = None

            # 3. process package(s) one by one
            #    the received data packages maybe spliced,
            #    if the message data was wrap by other transfer protocol,
            #    use the right split char(s) to split it
            while len(data) > 0:
                # 3.1. split data package(s)
                # TODO: split TCP spliced package(s)
                pos = data.find(b'\n')
                if pos < 0:
                    # partially data, push back for next loop
                    print('incomplete data:', data)
                    incomplete_data = data
                    break

                # 3.2. got one complete package
                pack = data[:pos+1]
                data = data[pos+1:]
                if pos == 0 or pack.isspace():
                    print('empty package, skip it')
                    continue

                # 3.3. unwrap & decode message
                try:
                    # TODO: unwrap the package
                    #    if the message data was wrap by other transfer protocol, unwrap it here.
                    #    if the package incomplete, raise ValueError.
                    msg = pack[:pos]

                    # decode the JsON string to dictionary
                    #    if the msg data error, raise ValueError.
                    msg = msg.decode('utf-8')
                    msg = json_dict(msg)
                except ValueError as error:
                    # TODO: handle error pack
                    print('!!! received message error:', error)
                    continue

                # 3.4. process the message
                msg = dimp.ReliableMessage(msg)
                response = self.processor.process(msg)
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s' % response)
                    msg = station.pack(receiver=msg.envelope.sender, content=response)
                    self.send_message(msg)

    def send_message(self, msg: dimp.ReliableMessage):
        data = json_str(msg) + '\n'
        data = data.encode('utf-8')
        self.request.sendall(data)
