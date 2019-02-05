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
        # incomplete data (maybe received partially)
        self.incomplete_data = None

    def setup(self):
        print(self, 'set up with', self.client_address)
        self.processor = MessageProcessor(handler=self)
        self.identifier = None
        self.incomplete_data = None

    def finish(self):
        if self.identifier:
            print('disconnect current request from session', self.identifier, self.client_address)
            response = dimp.TextContent.new(text='Bye!')
            msg = station.pack(receiver=self.identifier, content=response)
            self.send_message(msg)
            current = session_server.session(identifier=self.identifier)
            current.request_handler = None
        if self.incomplete_data is not None:
            print('!!! incomplete data:', self.incomplete_data.decode('utf-8'))
        print(self, 'finish')

    """
        main entrance
    """
    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)

        while station.running:
            # receive and unwrap messages
            packages = self.receive()
            if len(packages) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break
            # process message(s) one by one
            for pack in packages:
                # received data error
                if 'error' in pack:
                    # TODO: handle error pack
                    print('!!! received error data package:', pack)
                    # data = pack['data']
                    # self.request.sendall(data)
                    continue
                # process one message
                msg = dimp.ReliableMessage(pack)
                response = self.processor.process(msg)
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s' % response)
                    msg = station.pack(receiver=msg.envelope.sender, content=response)
                    self.send_message(msg)

    def receive(self) -> list:
        messages = []
        # 1. check the incomplete data
        if self.incomplete_data is None:
            data = b''
        else:
            data = self.incomplete_data
            self.incomplete_data = None
        # 2. receive all data
        while True:
            part = self.request.recv(1024)
            data += part
            if len(part) < 1024:
                break
        # 3. split data package(s)
        #    the received data packages maybe spliced,
        #    if the message data was wrap by other transfer protocol,
        #    use the right split char here
        packages = data.split(b'\n')

        # 4. unwrap each package & decode
        count = 0
        for pack in packages:
            count += 1
            if len(pack) == 0:
                # skip empty package
                continue
            # one line(pack) one message
            line = ''
            try:
                # 4.1. unwrap message package
                #    if the message data was wrap by other transfer protocol, unwrap it here.
                #    if the package incomplete, raise ValueError.
                data = pack

                # 4.2. decode message
                #    if incomplete data found, push it back for next time.
                line = data.decode('utf-8')
                messages.append(json_dict(line))
            except UnicodeDecodeError as error:
                print('decode error:', error)
                messages.append({'data': data, 'error': error})
            except ValueError as error:
                if count == packages.count:
                    # partially data, push back for next input
                    print('incomplete data:', line)
                    self.incomplete_data = pack
                else:
                    print('value error:', error)
                    messages.append({'data': line.encode('utf-8'), 'error': error})
        # 5. return all message(s) received
        return messages

    def send_message(self, msg: dimp.ReliableMessage):
        data = json_str(msg) + '\n'
        data = data.encode('utf-8')
        self.request.sendall(data)
