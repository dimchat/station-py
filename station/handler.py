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

import socket
import traceback
from socketserver import StreamRequestHandler
from typing import Optional, Union, List

from startrek import Connection, ActiveConnection
from startrek import GateDelegate, GateStatus
from startrek import Arrival, Departure, DepartureShip

from dimp import NetworkType, ID
from dimp import Content, Envelope, InstantMessage, ReliableMessage
from startrek import DeparturePriority

from libs.utils.log import Logging
from libs.utils import get_msg_sig
from libs.utils import NotificationCenter
from libs.network import GateKeeper, CommonGate
from libs.network import WSArrival, MarsStreamArrival, MTPStreamArrival
from libs.database import Database
from libs.common import NotificationNames
from libs.common import msg_traced, is_broadcast_message
from libs.server import Session, SessionServer
from libs.server import Dispatcher
from libs.server import AgentCaller, SearchEngineCaller

from station.config import g_messenger, g_station


g_database = Database()
g_dispatcher = Dispatcher()


class RequestHandler(StreamRequestHandler, Logging, Session, GateDelegate):

    MAX_SUSPENDED = 128

    def __init__(self, request, client_address, server):
        self.__keeper = self._create_gate_keeper(address=client_address, sock=request)
        self.__identifier: Optional[ID] = None
        self.__client_address: Optional[tuple] = None
        self.__suspended_messages: List[ReliableMessage] = []
        # init
        super().__init__(request=request, client_address=client_address, server=server)

    def _create_gate_keeper(self, address: tuple, sock: Optional[socket.socket]):
        return GateKeeper(address=address, sock=sock, messenger=g_messenger, delegate=self)

    @property
    def keeper(self) -> GateKeeper:
        return self.__keeper

    @property
    def gate(self) -> CommonGate:
        return self.keeper.gate

    @property  # Override
    def active(self) -> bool:
        return self.keeper.active

    @active.setter  # Override
    def active(self, flag: bool):
        self.keeper.active = flag

    @property  # Override
    def identifier(self) -> Optional[ID]:
        return self.__identifier

    @identifier.setter  # Override
    def identifier(self, value: ID):
        self.__identifier = value

    @property  # Override
    def client_address(self) -> tuple:
        return self.__client_address

    @client_address.setter
    def client_address(self, address: tuple):
        self.__client_address = address

    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s: %s id="%s", active=%s />' % (cname, self.client_address, self.identifier, self.active)

    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s: %s id="%s", active=%s />' % (cname, self.client_address, self.identifier, self.active)

    # Override
    def setup(self):
        super().setup()
        self.keeper.setup()
        SessionServer().add_session(session=self)
        self.info('client connected: %s' % self)

    # Override
    def handle(self):
        super().handle()
        self.info('session started: %s' % str(self))
        self.keeper.handle()
        self.info('session finished: %s' % str(self))

    # Override
    def finish(self):
        self.info('client disconnected: %s' % self)
        SessionServer().remove_session(session=self)
        self.keeper.finish()
        super().finish()

    def stop(self):
        self.keeper.stop()

    def __process_message(self, msg: ReliableMessage):
        """ processing message from socket """
        sender = msg.sender
        receiver = msg.receiver
        agent = AgentCaller()
        if receiver == g_station.identifier or receiver == 'station@anywhere':
            msg['client_address'] = self.client_address
            return agent.send(msg=msg)
        # check login
        if self.identifier is None:
            # not login yet
            self.debug(msg='not login yet, let the agent to shake hands with sender: %s' % sender)
            msg['client_address'] = self.client_address
            if self.__suspended_messages is None:
                self.__suspended_messages = [msg]
            else:
                if len(self.__suspended_messages) > self.MAX_SUSPENDED:
                    self.__suspended_messages.pop(0)
                self.__suspended_messages.append(msg)
            return agent.send(msg={
                'name': NotificationNames.CONNECTED,
                'info': {
                    'ID': str(sender),
                    'client_address': self.client_address,
                }
            })
        elif self.__suspended_messages is not None:
            # resend suspended message
            suspended_messages = self.__suspended_messages.copy()
            self.__suspended_messages = None
            for delayed in suspended_messages:
                self.__deliver_message(msg=delayed)
        return self.__deliver_message(msg=msg)

    def __deliver_message(self, msg: ReliableMessage):
        # check cycled
        sender = msg.sender
        receiver = msg.receiver
        if msg_traced(msg=msg, node=g_station.identifier, append=True):
            sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
            self.info('cycled msg [%s]: %s in %s' % (sig, g_station.identifier, msg.get('traces')))
            if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
                self.warning('ignore station msg [%s]: %s -> %s' % (sig, sender, receiver))
                return -2
            if is_broadcast_message(msg=msg):
                self.warning('ignore traced broadcast msg [%s]: %s -> %s' % (sig, sender, receiver))
                return -2
        # check receiver
        agent = AgentCaller()
        receiver = msg.receiver
        if receiver == g_station.identifier:
            self.info('forward msg to agent: %s -> %s' % (sender, receiver))
            msg['client_address'] = self.client_address
            return agent.send(msg=msg)
        if receiver in ['archivist@anywhere', 'archivists@everywhere']:
            self.info('forward search command to archivist: %s -> %s' % (sender, receiver))
            msg['client_address'] = self.client_address
            return SearchEngineCaller().send(msg=msg)
        if receiver.is_broadcast:
            # anyone@anywhere, everyone@everywhere
            # station@anywhere, stations@everywhere
            msg['client_address'] = self.client_address
            agent.send(msg=msg)
        else:
            g_database.save_message(msg=msg)
        res = g_dispatcher.deliver(msg=msg)
        if res is not None:
            self.send_content(content=res, receiver=sender, priority=DeparturePriority.NORMAL)

    def send_content(self, content: Content, receiver: ID, priority: Union[int, DeparturePriority]):
        env = Envelope.create(sender=g_station.identifier, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        s_msg = g_messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to encrypt message: %s' % env
        r_msg = g_messenger.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        self.send_reliable_message(msg=r_msg, priority=priority)

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: Union[int, DeparturePriority]) -> bool:
        if not self.active:
            # FIXME: connection lost?
            self.warning(msg='session inactive')
        self.debug(msg='sending msg to: %s, priority: %d' % (msg.receiver, priority))
        if msg.receiver == '0x620507866ccf492b89E36152e1Aea9f271980f85':
            self.error(msg='error')
        return self.keeper.send_reliable_message(msg=msg, priority=priority)

    #
    #   Gate Delegate
    #

    # Override
    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate):
        if current is None or current == GateStatus.ERROR:
            # connection error or session finished
            self.active = False
            self.stop()
            NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
                'session': self,
            })
        elif current == GateStatus.READY:
            # keep session info stay in redis
            SessionServer().update_session(session=self)
            # connected/reconnected
            NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
                'session': self,
            })

    # Override
    def gate_received(self, ship: Arrival, source: tuple, destination: Optional[tuple], connection: Connection):
        if isinstance(ship, MTPStreamArrival):
            payload = ship.payload
        elif isinstance(ship, MarsStreamArrival):
            payload = ship.payload
        elif isinstance(ship, WSArrival):
            payload = ship.payload
        else:
            raise ValueError('unknown arrival ship: %s' % ship)
        # check payload
        if payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        elif len(payload) > 0:
            packages = [payload]
        else:
            self.warning(msg='received empty package: %s -> %s' % (source, destination))
            packages = []
        # try to process each package
        for pack in packages:
            try:
                msg = g_messenger.deserialize_message(data=pack)
                self.__process_message(msg=msg)
            except Exception as error:
                self.error('parse message failed (%s): %s, %s' % (source, error, pack))
                self.error('payload: %s' % payload)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        # respond for Tencent/mars
        if isinstance(ship, MarsStreamArrival) and len(payload) > 0:
            if connection is not None and not isinstance(connection, ActiveConnection):
                # station MUST respond something to client request (Tencent Mars)
                self.gate.send_response(payload=b'', ship=ship, remote=source, local=destination)

    # Override
    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_sent(ship=ship, source=source, destination=destination, connection=connection)

    # Override
    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_error(error=error, ship=ship, source=source, destination=destination, connection=connection)
