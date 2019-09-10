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

from dimp import ID
from dimp import TextContent, ReliableMessage

from common import Log
from common import NetMsgHead, NetMsg
from common import Session

from .processor import MessageProcessor

from .config import g_facebook, g_session_server, g_monitor, current_station


class RequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # message processor
        self.processor = None
        # current session (with identifier as remote user ID)
        self.session = None

    @property
    def identifier(self) -> ID:
        if self.session is not None:
            return self.session.identifier

    def current_session(self, identifier: ID=None) -> Session:
        # check whether the current session's identifier matched
        if identifier is None:
            return self.session
        if self.session is not None:
            # current session belongs to the same user
            if self.session.identifier == identifier:
                return self.session
            # user switched, clear current session
            g_session_server.remove_session(session=self.session)
            self.session = None
        # get new session with identifier
        self.session = g_session_server.session_create(identifier=identifier, request_handler=self)
        return self.session

    def send(self, data: bytes) -> bool:
        try:
            self.request.sendall(data)
            return True
        except IOError as error:
            Log.info('RequestHandler: failed to send data %s' % error)
            return False

    def receive(self, buffer_size=1024) -> bytes:
        try:
            return self.request.recv(buffer_size)
        except IOError as error:
            Log.info('RequestHandler: failed to receive data %s' % error)

    #
    #
    #

    def setup(self):
        Log.info('%s: set up with %s' % (self, self.client_address))
        g_monitor.report(message='Client connected %s [%s]' % (self.client_address, current_station.name))
        # message processor
        self.processor = MessageProcessor(request_handler=self)
        # current session
        self.session = None

    def finish(self):
        if self.session is not None:
            nickname = g_facebook.nickname(identifier=self.identifier)
            Log.info('RequestHandler: disconnect from session %s, %s' % (self.identifier, self.client_address))
            g_monitor.report(message='User %s logged out %s %s' % (nickname, self.client_address, self.identifier))
            response = TextContent.new(text='Bye!')
            msg = current_station.pack(receiver=self.identifier, content=response)
            self.push_message(msg)
            # clear current session
            g_session_server.remove_session(session=self.session)
            self.session = None
        else:
            g_monitor.report(message='Client disconnected %s [%s]' % (self.client_address, current_station.name))
        Log.info('RequestHandler: finish (%s, %s)' % self.client_address)

    """
        DIM Request Handler
    """
    def handle(self):
        Log.info('RequestHandler: client connected (%s, %s)' % self.client_address)
        data = b''
        while current_station.running:
            # receive all data
            incomplete_length = len(data)
            while True:
                part = self.receive(1024)
                if part is None:
                    break
                data += part
                if len(part) < 1024:
                    break
            if len(data) == incomplete_length:
                Log.info('RequestHandler: no more data, exit (%d, %s)' % (incomplete_length, self.client_address))
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
                    Log.info('RequestHandler: not mars message pack: %s' % error)
                # check mars head
                if mars:
                    Log.info('@@@ msg via mars, len: %d+%d' % (head.head_length, head.body_length))
                    # check completion
                    pack_len = head.head_length + head.body_length
                    if pack_len > len(data):
                        # partially data, keep it for next loop
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
                        break
                    # cut out the first package from received data
                    pack = data[:pos+1]
                    data = data[pos+1:]
                    self.handle_raw_package(pack)
                    # raw data OK
                    continue

                # (Protocol ?)
                # TODO: split and unwrap data package(s)
                Log.info('RequestHandler: unknown protocol %s' % data)
                data = b''
                # raise AssertionError('unknown protocol')

    #
    #
    #

    def handle_mars_package(self, pack: bytes):
        pack = NetMsg(pack)
        head = pack.head
        Log.info('@@@ processing package: cmd=%d, seq=%d' % (head.cmd, head.seq))
        if head.cmd == 3:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('messages not found')
            # maybe more than one message in a pack
            lines = pack.body.splitlines()
            body = b''
            for line in lines:
                if line.isspace():
                    Log.info('RequestHandler: ignore empty message')
                    continue
                response = self.process_message(line)
                if response:
                    msg = json.dumps(response) + '\n'
                    body = body + msg.encode('utf-8')
            if body:
                data = NetMsg(cmd=head.cmd, seq=head.seq, body=body)
                # Log.info('RequestHandler: mars response', data)
                self.send(data)
            else:
                # TODO: handle error message
                Log.info('RequestHandler: nothing to response')
        elif head.cmd == 6:
            # TODO: handle NOOP request
            Log.info('RequestHandler: receive NOOP package, response %s' % pack)
            self.send(pack)
        else:
            # TODO: handle Unknown request
            Log.info('RequestHandler: unknown package %s' % pack)
            self.send(pack)

    def handle_raw_package(self, pack: bytes):
        response = self.process_message(pack)
        if response:
            msg = json.dumps(response) + '\n'
            data = msg.encode('utf-8')
            self.send(data)
        else:
            Log.info('RequestHandler: process error %s' % pack)
            # self.send(pack)

    def process_message(self, pack: bytes):
        # decode the JsON string to dictionary
        # if the msg data error, raise ValueError.
        try:
            msg = json.loads(pack.decode('utf-8'))
            msg = ReliableMessage(msg)
            res = self.processor.process(msg)
            if res:
                # Log.info('RequestHandler: response to client', self.client_address, res)
                receiver = g_facebook.identifier(msg.envelope.sender)
                return current_station.pack(receiver=receiver, content=res)
        except Exception as error:
            Log.info('RequestHandler: receive message package error %s' % error)

    def push_mars_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg) + '\n'
        body = data.encode('utf-8')
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        data = NetMsg(cmd=10001, seq=0, body=body)
        # Log.info('RequestHandler: pushing mars message', data)
        return self.send(data)

    def push_raw_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg) + '\n'
        data = data.encode('utf-8')
        # Log.info('RequestHandler: pushing raw message', data)
        return self.send(data)

    push_message = push_raw_message
