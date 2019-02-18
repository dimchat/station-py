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
from .mars import NetMsgHead, NetMsg


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
                    if head.client_version == 200:
                        # OK, it seems be a mars package!
                        mars = True
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
                    # process mars package
                    if head.cmd_id == 6:
                        print('@@@ receive NOOP package: seq=%d' % head.seq)
                        # TODO: handle NOOP request
                        print('    response:', pack)
                        self.request.sendall(pack)
                    elif head.body_length > 0:
                        print('@@@ processing package: cmd=%d, seq=%d' % (head.cmd_id, head.seq))
                        body = pack[head.head_length:]
                        # array = body.splitlines()
                        # for pack in array:
                        #     msg = self.process_message(pack)
                        #     if msg:
                        #         self.send_mars_msg(msg, head)
                        #     else:
                        #         self.send_mars_err(pack, head)
                        msg = self.process_message(body)
                        if msg:
                            self.send_mars_msg(msg, head)
                        else:
                            self.send_mars_err(pack, head)
                    # mars OK
                    continue

                # (Protocol B) raw data with no wrap?
                if data.startswith(b'{"') and data.find(b'\0') < 0:
                    # check completion
                    pos = data.find(b'\n')
                    if pos < 0:
                        # partially data, keep it for next loop
                        print('incomplete data:', data)
                        break
                    # cut out the first package from received data
                    pack = data[:pos+1]
                    data = data[pos+1:]
                    msg = self.process_message(pack)
                    if msg:
                        self.send_message(msg)
                    else:
                        self.send_error(pack)
                    # raw data OK
                    continue

                # (Protocol ?)
                # TODO: split and unwrap data package(s)
                print('!!! unknown protocol:', data)
                data = b''
                # raise AssertionError('unknown protocol')

    def process_message(self, pack: bytes) -> dimp.ReliableMessage:
        # decode the JsON string to dictionary
        #    if the msg data error, raise ValueError.
        try:
            msg = json_dict(pack.decode('utf-8'))
            msg = dimp.ReliableMessage(msg)
            response = self.processor.process(msg)
            if response:
                print('*** response to client (%s:%s)...' % self.client_address)
                print('    content: %s' % response)
                return station.pack(receiver=msg.envelope.sender, content=response)
        except Exception as error:
            print('!!! receive message package: %s, error:%s' % (pack, error))

    def send_mars_msg(self, msg: dimp.ReliableMessage, head: NetMsgHead):
        body = json_str(msg).encode('utf-8')
        pack = NetMsg(cmd_id=head.cmd_id, seq=head.seq + 1, body=body)
        print('    response:', pack)
        self.request.sendall(pack)

    def send_mars_err(self, pack: bytes, head: NetMsgHead):
        # TODO: handle error request
        pack = NetMsg(cmd_id=head.cmd_id, seq=head.seq + 1, body=pack)
        print('    response:', pack)
        self.request.sendall(pack)

    def send_message(self, msg: dimp.ReliableMessage):
        data = json_str(msg) + '\n'
        data = data.encode('utf-8')
        self.request.sendall(data)

    def send_error(self, pack: bytes):
        # TODO: handle error request
        print('!!!error:', pack)
        self.request.sendall(pack)
