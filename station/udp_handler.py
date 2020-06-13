# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    UDP Server
    ~~~~~~~~~~

"""
import traceback
from typing import Union

import udp
import dmtp
import dimp

from libs.common import Log

from .config import g_facebook


class Server(dmtp.Server):

    def __init__(self, hub: udp.Hub):
        super().__init__()
        hub.add_listener(self.peer)
        self.__hub = hub

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def say_hi(self, destination: tuple) -> bool:
        cmd = dmtp.HelloCommand.new(identifier='station@anywhere')
        print('sending cmd: %s' % cmd)
        self.send_command(cmd=cmd, destination=destination)
        return True

    def __analyze_location(self, location: dmtp.LocationValue) -> int:
        if location is None:
            self.error('location should not empty')
            return -1
        if location.identifier is None:
            self.error('user ID should not empty')
            return -2
        else:
            uid = g_facebook.identifier(string=location.identifier)
            if uid is None:
                self.error('user ID error: %s' % location.identifier)
                return -2
            user = g_facebook.user(identifier=uid)
            if user is None:
                self.error('failed to get user with ID: %s' % uid)
                return -2
        if location.mapped_address is None:
            self.error('mapped address should not empty')
            return -3
        if location.signature is None:
            self.error('location not signed')
            return -4
        # data = "source_address" + "mapped_address" + "relayed_address" + "time"
        data = location.mapped_address.data
        if location.source_address is not None:
            data = location.source_address.data + data
        if location.relayed_address is not None:
            data = data + location.relayed_address.data
        timestamp = dmtp.TimestampValue(value=location.timestamp)
        data += timestamp.data
        signature = location.signature
        # verify data and signature with public key
        if user.verify(data=data, signature=signature):
            return uid.number
        self.error('location signature not match: %s' % location)
        return 0

    def set_location(self, location: dmtp.LocationValue) -> bool:
        if self.__analyze_location(location=location) <= 0:
            self.info('location not acceptable: %s' % location)
            return False
        return super().set_location(location=location)

    def process_command(self, cmd: dmtp.Command, source: tuple) -> bool:
        # noinspection PyBroadException
        try:
            return super().process_command(cmd=cmd, source=source)
        except Exception:
            traceback.print_exc()
            return False

    @staticmethod
    def __fetch_meta(msg: dimp.ReliableMessage) -> bool:
        sender = g_facebook.identifier(msg.envelope.sender)
        meta = dimp.Meta(meta=msg.meta)
        if meta is not None:
            return g_facebook.save_meta(meta=meta, identifier=sender)

    def process_message(self, msg: dmtp.Message, source: tuple) -> bool:
        # noinspection PyBroadException
        try:
            self.info('received msg: %s' % msg)
            dictionary = msg.to_dict()
            r_msg = dimp.ReliableMessage(msg=dictionary)
            self.info('reliable message: %s' % r_msg)
            if r_msg is not None:
                self.__fetch_meta(msg=r_msg)
                # TODO: process message
            return True
        except Exception:
            traceback.print_exc()
            return False

    #
    #   PeerDelegate
    #
    def send_data(self, data: bytes, destination: tuple, source: Union[tuple, int] = None) -> int:
        self.__hub.send(data=data, destination=destination, source=source)
        return 0


def create_udp_server(port: int, host='0.0.0.0') -> Server:
    # create a hub for sockets
    hub = udp.Hub()
    hub.open(host=host, port=port)
    hub.start()

    # create server
    print('>>> UDP server (%s:%d) starting ...' % (host, port))
    return Server(hub=hub)
