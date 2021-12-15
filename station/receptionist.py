#! /usr/bin/env python3
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
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""

import threading
import traceback
from typing import Optional, Union, Set, List

from startrek.fsm import Runner

from dimp import ID, NetworkType
from dimp import Envelope, Content, Command
from dimp import InstantMessage, ReliableMessage
from dimp import Transceiver
from dimsdk import HandshakeCommand
from dimsdk import CommandProcessor, ProcessorFactory

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import Log, Logging
from libs.utils.ipc import ShuttleBus, ReceptionistArrows
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames

from libs.server import ServerProcessor, ServerProcessorFactory
from libs.server import ServerMessenger

from etc.cfg_init import g_database
from station.config import g_facebook, g_station


class ReceptionistWorker(Runner, Logging, NotificationObserver):

    def __init__(self):
        super().__init__()
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_ROAMING)
        # waiting queue for offline messages
        self.__guests = set()
        self.__lock = threading.Lock()
        # pipe
        bus = ShuttleBus()
        bus.set_arrows(arrows=ReceptionistArrows.secondary(delegate=bus))
        bus.start()
        self.__bus: ShuttleBus[dict] = bus

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__bus.send(obj=msg)

    # Override
    def process(self) -> bool:
        msg = self.__bus.receive()
        # process roamers
        try:
            if msg is None:
                self.__process_users(users=self.get_guests())
            elif msg.get('name') is not None and msg.get('info') is not None:
                self.__process_notification(event=msg)
            else:
                msg = ReliableMessage.parse(msg=msg)
                self.__process_message(msg=msg)
                return True
        except Exception as error:
            self.error('receptionist error: %s, %s' % (msg, error))
            traceback.print_exc()

    def __process_message(self, msg: ReliableMessage):
        responses = g_messenger.process_reliable_message(msg=msg)
        for res in responses:
            self.send(msg=res)

    def __process_notification(self, event: dict):
        name = event.get('name')
        info = event.get('info')
        if name in [NotificationNames.USER_LOGIN, NotificationNames.USER_ONLINE]:
            identifier = ID.parse(identifier=info.get('ID'))
            if identifier is not None:
                self.add_guest(identifier=identifier)

    def __process_users(self, users: Set[ID]):
        for identifier in users:
            # 1. get cached messages
            messages = g_database.messages(receiver=identifier)
            self.info('%d message(s) loaded for: %s' % (len(messages), identifier))
            # 2. sent messages one by one
            for msg in messages:
                self.send(msg=msg)

    def get_guests(self) -> Set[ID]:
        with self.__lock:
            guests = self.__guests.copy()
            self.__guests.clear()
            return guests

    def add_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.add(identifier)

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        user = ID.parse(identifier=info.get('ID'))
        if user is None or user.type == NetworkType.STATION:
            self.error('ignore notification: %s' % info)
        elif name == NotificationNames.USER_ONLINE:
            # sid = info.get('station')
            # if sid is not None and sid != self.station:
            self.add_guest(identifier=user)
        elif name == NotificationNames.USER_ROAMING:
            # add the new roamer for checking cached messages
            self.add_guest(identifier=user)


#
#   DIMP
#


class HandshakeCommandProcessor(CommandProcessor, Logging):

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, HandshakeCommand), 'command error: %s' % cmd
        message = cmd.message
        if message in ['DIM?', 'DIM!']:
            # S -> C
            text = 'Handshake command error: %s' % message
            self.error(msg=text)
            return self._respond_text(text=text)
        # C -> S: Hello world!
        assert 'Hello world!' == message, 'Handshake command error: %s' % cmd
        remote = msg.get('client_address')
        assert isinstance(remote, tuple), 'remote address error: %s' % remote
        session = g_database.fetch_session(address=remote)
        session_key = session['key']
        self.debug(msg='session info: %s, %s, %s' % (msg.sender, remote, session_key))
        if session_key != cmd.session:
            res = HandshakeCommand.again(session=session.key)
            return [res]
        else:
            # session verify success
            g_database.update_session(address=remote, identifier=msg.sender)
            g_worker.send(msg={
                'command': 'handshake accepted',
                'ID': msg.sender,
                'session_key': session_key,
                'client_address': remote,
            })
            res = HandshakeCommand.success(session=session_key)
            return [res]


class ReceptionistProcessorFactory(ServerProcessorFactory):

    # Override
    def _create_command_processor(self, msg_type: int, cmd_name: str) -> Optional[CommandProcessor]:
        # handshake
        if cmd_name == Command.HANDSHAKE:
            return HandshakeCommandProcessor(messenger=self.messenger)
        # others
        return super()._create_command_processor(msg_type=msg_type, cmd_name=cmd_name)


class ReceptionistMessageProcessor(ServerProcessor):

    # Override
    def _create_processor_factory(self) -> ProcessorFactory:
        return ReceptionistProcessorFactory(messenger=self.messenger)

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        # TODO: override to check group
        cpu = self.get_processor(content=content)
        return cpu.process(content=content, msg=r_msg)
        # TODO: override to filter the response


class ReceptionistMessenger(ServerMessenger):

    # Override
    def _create_processor(self) -> Transceiver.Processor:
        return ReceptionistMessageProcessor(messenger=self)

    # Override
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        g_worker.send(msg=msg)
        return []

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        g_worker.send(msg=msg)
        return True

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        s_msg = g_messenger.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            return False
        r_msg = g_messenger.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set msg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        self.send_reliable_message(msg=r_msg, priority=priority)

    # Override
    def send_content(self, content: Content, priority: int, receiver: ID, sender: ID = None) -> bool:
        if sender is None:
            user = g_messenger.facebook.current_user
            assert user is not None, 'current user not set'
            sender = user.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        msg = InstantMessage.create(head=env, body=content)
        return self.send_instant_message(msg=msg, priority=priority)


g_worker = ReceptionistWorker()
g_messenger = ReceptionistMessenger()


if __name__ == '__main__':
    Log.info(msg='>>> starting receptionist ...')
    g_facebook.current_user = g_station
    g_worker.run()
    Log.info(msg='>>> receptionist exists.')
