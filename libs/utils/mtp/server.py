# -*- coding: utf-8 -*-

import json
import socket
import threading
import time
import traceback
from typing import Optional, Dict

from udp.ba import Data
from udp.mtp import Header
from udp import Channel, Connection, ConnectionDelegate
from udp import DiscreteChannel, PackageHub

import dmtp

from ...utils import Log

from .manager import ContactManager, FieldValueEncoder


class ServerHub(PackageHub):

    def __init__(self, delegate: ConnectionDelegate):
        super().__init__(delegate=delegate)
        self.__connections: Dict[tuple, Connection] = {}
        self.__sockets: Dict[tuple, socket.socket] = {}

    def bind(self, local: tuple) -> Connection:
        sock = self.__sockets.get(local)
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(local)
            sock.setblocking(False)
            self.__sockets[local] = sock
        return self.connect(remote=None, local=local)

    # Override
    def create_connection(self, remote: Optional[tuple], local: Optional[tuple]) -> Connection:
        conn = self.__connections.get(local)
        if conn is None:
            conn = super().create_connection(remote=None, local=local)
            self.__connections[local] = conn
        return conn

    # Override
    def create_channel(self, remote: Optional[tuple], local: Optional[tuple]) -> Channel:
        sock = self.__sockets.get(local)
        if sock is not None:
            return DiscreteChannel(sock=sock)
        else:
            raise LookupError('failed to get channel: %s -> %s' % (remote, local))


class Server(dmtp.Server, ConnectionDelegate):

    def __init__(self, host: str, port: int):
        super().__init__()
        self.__local_address = (host, port)
        self.__hub = ServerHub(delegate=self)
        self.__db: Optional[ContactManager] = None
        self.__running = False

    @property
    def database(self) -> ContactManager:
        return self.__db

    @database.setter
    def database(self, db: ContactManager):
        self.__db = db

    @property
    def identifier(self) -> str:
        return self.__db.identifier

    @identifier.setter
    def identifier(self, uid: str):
        self.__db.identifier = uid

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    # Override
    def _connect(self, remote: tuple):
        try:
            self.__hub.connect(remote=remote, local=self.__local_address)
        except socket.error as error:
            self.error('failed to connect to %s: %s' % (remote, error))

    # Override
    def connection_state_changing(self, connection: Connection, current_state, next_state):
        self.info('!!! connection (%s, %s) state changed: %s -> %s'
                  % (connection.local_address, connection.remote_address, current_state, next_state))

    # Override
    def connection_data_received(self, connection: Connection, remote: tuple, wrapper, payload: bytes):
        if isinstance(wrapper, Header) and len(payload) > 0:
            body = Data(buffer=payload)
            self._received(head=wrapper, body=body, source=remote)

    # Override
    def _process_command(self, cmd: dmtp.Command, source: tuple) -> bool:
        self.info('received cmd: %s' % cmd)
        # noinspection PyBroadException
        try:
            return super()._process_command(cmd=cmd, source=source)
        except Exception as error:
            self.error('failed to process command (%s): %s' % (cmd, error))
            traceback.print_exc()
            return False

    # Override
    def _process_message(self, msg: dmtp.Message, source: tuple) -> bool:
        self.info('received msg from %s:\n\t%s' % (source, json.dumps(msg, cls=FieldValueEncoder)))
        # return super().process_message(msg=msg, source=source)
        return True

    # Override
    def send_command(self, cmd: dmtp.Command, destination: tuple) -> bool:
        self.info('sending cmd to %s:\n\t%s' % (destination, cmd))
        try:
            body = cmd.get_bytes()
            source = self.__local_address
            self.__hub.send_command(body=body, source=source, destination=destination)
            return True
        except socket.error as error:
            self.error('failed to send command: %s' % error)

    # Override
    def send_message(self, msg: dmtp.Message, destination: tuple) -> bool:
        self.info('sending msg to %s:\n\t%s' % (destination, json.dumps(msg, cls=FieldValueEncoder)))
        try:
            body = msg.get_bytes()
            source = self.__local_address
            self.__hub.send_message(body=body, source=source, destination=destination)
            return True
        except socket.error as error:
            self.error('failed to send message: %s' % error)

    #
    #   Server actions
    #

    # Override
    def say_hello(self, destination: tuple) -> bool:
        if super().say_hello(destination=destination):
            return True
        cmd = dmtp.Command.hello_command(identifier=self.identifier)
        self.send_command(cmd=cmd, destination=destination)
        return True

    def start(self):
        self.__hub.bind(local=self.__local_address)
        self.__running = True
        threading.Thread(target=self.run).start()

    def run(self):
        while self.__running:
            self.__hub.tick()
            time.sleep(0.128)
