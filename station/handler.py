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
    Request Handler
    ~~~~~~~~~~~~~~~

    Handler for each connection
"""
import json
from socketserver import BaseRequestHandler

import dimp

from .mars import NetMsgHead, NetMsg
from .processor import MessageProcessor
from .session import Session

from .config import station, session_server


class RequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # message processor
        self.processor = None
        # current session (with identifier as remote user ID)
        self.session = None

    @property
    def identifier(self) -> dimp.ID:
        if self.session is not None:
            return self.session.identifier

    def clear_session(self):
        if self.session:
            session_server.remove_session(session=self.session)
            self.session = None

    def current_session(self, identifier: dimp.ID) -> Session:
        # check whether the current session's identifier matched
        if self.session is not None and self.session.identifier != identifier:
            # user switched, clear to reset session
            self.clear_session()
        # get new session with identifier
        if self.session is None:
            self.session = session_server.session_create(identifier=identifier, request_handler=self)
        return self.session

    def setup(self):
        print(self, 'set up with', self.client_address)
        self.processor = MessageProcessor(request_handler=self)
        self.session = None

    def finish(self):
        if self.session is not None:
            print('disconnect current request from session', self.identifier, self.client_address)
            response = dimp.TextContent.new(text='Bye!')
            msg = station.pack(receiver=self.identifier, content=response)
            self.push_message(msg)
            self.clear_session()
        print(self, 'finish', self.client_address)

    """
        DIM Request Handler
    """
    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)
        data = b''
        while station.running:
            # receive all data
            while True:
                part = self.request.recv(1024)
                data += part
                if len(part) < 1024:
                    break
            if len(data) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break

            # process package(s) one by one
            #    the received data packages maybe spliced,
            #    if the message data was wrap by other transfer protocol,
            #    use the right split char(s) to split it
            while len(data) > 0:

                # (Protocol A) Tencent mars?
                mars = False
                head = None
                try:
                    head = NetMsgHead(data=data)
                    if head.version == 200:
                        # OK, it seems be a mars package!
                        mars = True
                        self.push_message = self.push_mars_message
                except ValueError as error:
                    print('not mars message pack:', error)
                # check mars head
                if mars:
                    print('@@@ msg via mars, len: %d+%d' % (head.head_length, head.body_length))
                    # check completion
                    pack_len = head.head_length + head.body_length
                    if pack_len > len(data):
                        # partially data, keep it for next loop
                        print('incomplete data:', data)
                        break
                    # cut out the first package from received data
                    pack = data[:pack_len]
                    data = data[pack_len:]
                    self.handle_mars_package(pack)
                    # mars OK
                    continue

                # (Protocol B) raw data with no wrap?
                if data.startswith(b'{"') and data.find(b'\0') < 0:
                    # OK, it seems be a raw package!
                    self.push_message = self.push_raw_message

                    # check completion
                    pos = data.find(b'\n')
                    if pos < 0:
                        # partially data, keep it for next loop
                        print('incomplete data:', data)
                        break
                    # cut out the first package from received data
                    pack = data[:pos+1]
                    data = data[pos+1:]
                    self.handle_raw_package(pack)
                    # raw data OK
                    continue

                # (Protocol ?)
                # TODO: split and unwrap data package(s)
                print('!!! unknown protocol:', data)
                data = b''
                # raise AssertionError('unknown protocol')

    def handle_mars_package(self, pack: bytes):
        pack = NetMsg(pack)
        head = pack.head
        print('@@@ processing package: cmd=%d, seq=%d' % (head.cmd, head.seq))
        if head.cmd == 3:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('messages not found')
            # maybe more than one message in a pack
            lines = pack.body.splitlines()
            body = b''
            for line in lines:
                if line.isspace():
                    print('ignore empty message')
                    continue
                response = self.process_message(line)
                if response:
                    msg = json.dumps(response) + '\n'
                    body = body + msg.encode('utf-8')
            if body:
                data = NetMsg(cmd=head.cmd, seq=head.seq, body=body)
                print('    mars response:', data)
                self.request.sendall(data)
            else:
                # TODO: handle error message
                print('    nothing to response')
        elif head.cmd == 6:
            # TODO: handle NOOP request
            print('    receive NOOP package, response:', pack)
            self.request.sendall(pack)
        else:
            # TODO: handle Unknown request
            print('    unknown package:', pack)
            self.request.sendall(pack)

    def handle_raw_package(self, pack: bytes):
        response = self.process_message(pack)
        if response:
            msg = json.dumps(response) + '\n'
            data = msg.encode('utf-8')
            self.request.sendall(data)
        else:
            print('!!! error:', pack)
            # self.request.sendall(pack)

    def process_message(self, pack: bytes):
        # decode the JsON string to dictionary
        #    if the msg data error, raise ValueError.
        try:
            msg = json.loads(pack.decode('utf-8'))
            msg = dimp.ReliableMessage(msg)
            res = self.processor.process(msg)
            if res:
                print('*** response to client (%s:%s)...' % self.client_address)
                print('    content: %s' % res)
                receiver = dimp.ID(msg.envelope.sender)
                return station.pack(receiver=receiver, content=res)
        except Exception as error:
            print('!!! receive message package: %s, error:%s' % (pack, error))

    def push_mars_message(self, msg: dimp.ReliableMessage):
        data = json.dumps(msg) + '\n'
        body = data.encode('utf-8')
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        data = NetMsg(cmd=10001, seq=0, body=body)
        print('### pushing mars message:', data)
        self.request.sendall(data)

    def push_raw_message(self, msg: dimp.ReliableMessage):
        data = json.dumps(msg) + '\n'
        data = data.encode('utf-8')
        print('### pushing message:', data)
        self.request.sendall(data)

    push_message = push_raw_message
