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

from mkm import is_broadcast
from dimp import ID
from dimp import Content, TextContent, ReceiptCommand
from dimp import InstantMessage, SecureMessage, ReliableMessage

from common import Log
from common import NetMsgHead, NetMsg
from common import Session, Server

from .processor import MessageProcessor

from .config import g_facebook, g_session_server, g_monitor, g_dispatcher
from .config import current_station, local_servers
from .cfg_gsp import station_name


class RequestHandler(BaseRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request=request, client_address=client_address, server=server)
        # message processor
        self.processor: MessageProcessor = None
        # current session (with identifier as remote user ID)
        self.session: Session = None
        # current station
        self.station: Server = None

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

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

    def check_session(self, identifier: ID) -> Content:
        session = self.current_session(identifier=identifier)
        if not session.valid:
            # session invalid, handshake first
            # NOTICE: if the client try to send message to another user before handshake,
            #         the message will be lost!
            return self.processor.process_handshake(sender=identifier)

    def verify_message(self, msg: ReliableMessage) -> SecureMessage:
        return self.station.verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage) -> InstantMessage:
        station = None
        receiver = g_facebook.identifier(msg.envelope.receiver)
        if receiver.type.is_station():
            # check local stations
            if self.station.identifier == receiver:
                station = self.station
            else:
                # sent to other local station
                for srv in local_servers:
                    if srv.identifier == receiver:
                        # got it
                        station = srv
                        self.station = station
                        break
        elif is_broadcast(identifier=receiver):
            # anyone
            station = self.station
        if station is not None:
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            return station.decrypt_message(msg)

    def send(self, data: bytes) -> bool:
        try:
            self.request.sendall(data)
            return True
        except IOError as error:
            self.error('failed to send data %s' % error)
            return False

    def receive(self, buffer_size=1024) -> bytes:
        try:
            return self.request.recv(buffer_size)
        except IOError as error:
            self.error('failed to receive data %s' % error)

    def deliver_message(self, msg: ReliableMessage) -> Content:
        self.info('deliver message %s, %s' % (self.identifier, msg.envelope))
        g_dispatcher.deliver(msg)
        # response to sender
        response = ReceiptCommand.receipt(message='Message delivering')
        # extra info
        sender = msg.get('sender')
        receiver = msg.get('receiver')
        time = msg.get('time')
        group = msg.get('group')
        signature = msg.get('signature')
        # envelope
        response['sender'] = sender
        response['receiver'] = receiver
        if time is not None:
            response['time'] = time
        # group message?
        if group is not None and group != receiver:
            response['group'] = group
        # signature
        response['signature'] = signature
        return response

    def process_message(self, msg: ReliableMessage) -> Content:
        # verify signature
        s_msg = self.verify_message(msg)
        if s_msg is None:
            self.info('message verify error %s' % msg)
            response = TextContent.new(text='Signature error')
            response['signature'] = msg.signature
            return response
        # try to decrypt by station
        i_msg = self.decrypt_message(msg=s_msg)
        if i_msg is not None:
            # decrypt OK, process by current station
            res = self.processor.process(msg=i_msg)
            if res is not None:
                # finished
                return res
        # check session valid
        sender = g_facebook.identifier(msg.envelope.sender)
        res = self.check_session(identifier=sender)
        if res is not None:
            # handshake first
            return res
        # deliver message for receiver
        return self.deliver_message(msg)

    def process_package(self, pack: bytes):
        # decode the JsON string to dictionary
        # if the msg data error, raise ValueError.
        try:
            msg = json.loads(pack.decode('utf-8'))
            r_msg = ReliableMessage(msg)
            res = self.process_message(msg=r_msg)
            if res:
                # self.info('response to client %s, %s' % (self.client_address, res))
                receiver = g_facebook.identifier(r_msg.envelope.sender)
                return self.station.pack(content=res, receiver=receiver)
        except Exception as error:
            self.error('receive message package error %s' % error)

    #
    #
    #

    def setup(self):
        self.info('%s: set up with %s' % (self, self.client_address))
        g_monitor.report(message='Client connected %s [%s]' % (self.client_address, station_name))
        # message processor
        self.processor = MessageProcessor(request_handler=self)
        # current session
        self.session = None
        # current station
        self.station = current_station

    def finish(self):
        if self.session is not None:
            nickname = g_facebook.nickname(identifier=self.identifier)
            self.info('disconnect from session %s, %s' % (self.identifier, self.client_address))
            g_monitor.report(message='User %s logged out %s %s' % (nickname, self.client_address, self.identifier))
            response = TextContent.new(text='Bye!')
            msg = self.station.pack(receiver=self.identifier, content=response)
            self.push_message(msg)
            # clear current session
            g_session_server.remove_session(session=self.session)
            self.session = None
        else:
            g_monitor.report(message='Client disconnected %s [%s]' % (self.client_address, station_name))
        self.info('finish (%s, %s)' % self.client_address)

    """
        DIM Request Handler
    """
    def handle(self):
        self.info('client connected (%s, %s)' % self.client_address)
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
                self.info('no more data, exit (%d, %s)' % (incomplete_length, self.client_address))
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
                    self.error('not mars message pack: %s' % error)
                # check mars head
                if mars:
                    self.info('@@@ msg via mars, len: %d+%d' % (head.head_length, head.body_length))
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
                self.error('unknown protocol %s' % data)
                data = b''
                # raise AssertionError('unknown protocol')

    #
    #
    #

    def handle_mars_package(self, pack: bytes):
        pack = NetMsg(pack)
        head = pack.head
        self.info('@@@ processing package: cmd=%d, seq=%d' % (head.cmd, head.seq))
        if head.cmd == 3:
            # TODO: handle SEND_MSG request
            if head.body_length == 0:
                raise ValueError('messages not found')
            # maybe more than one message in a pack
            lines = pack.body.splitlines()
            body = b''
            for line in lines:
                if line.isspace():
                    self.info('ignore empty message')
                    continue
                response = self.process_package(line)
                if response:
                    msg = json.dumps(response) + '\n'
                    body = body + msg.encode('utf-8')
            if body:
                data = NetMsg(cmd=head.cmd, seq=head.seq, body=body)
                # self.info('mars response %s' % data)
                self.send(data)
            else:
                # TODO: handle error message
                self.info('nothing to response')
        elif head.cmd == 6:
            # TODO: handle NOOP request
            self.info('receive NOOP package, response %s' % pack)
            self.send(pack)
        else:
            # TODO: handle Unknown request
            self.error('unknown package %s' % pack)
            self.send(pack)

    def handle_raw_package(self, pack: bytes):
        response = self.process_package(pack)
        if response:
            msg = json.dumps(response) + '\n'
            data = msg.encode('utf-8')
            self.send(data)
        else:
            self.error('process error %s' % pack)
            # self.send(pack)

    def push_mars_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg) + '\n'
        body = data.encode('utf-8')
        # kPushMessageCmdId = 10001
        # PUSH_DATA_TASK_ID = 0
        data = NetMsg(cmd=10001, seq=0, body=body)
        # self.info('pushing mars message %s' % data)
        return self.send(data)

    def push_raw_message(self, msg: ReliableMessage) -> bool:
        data = json.dumps(msg) + '\n'
        data = data.encode('utf-8')
        # self.info('pushing raw message %s' % data)
        return self.send(data)

    push_message = push_raw_message
