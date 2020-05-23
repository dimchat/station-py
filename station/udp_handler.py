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
from typing import Optional, Union

import udp
import dmtp

from libs.common import Log

from .config import g_facebook


class Server(dmtp.Server):

    def __init__(self, hub: udp.Hub):
        super().__init__()
        hub.add_listener(self.peer)
        self.__hub = hub
        self.__locations = {}

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def set_location(self, value: dmtp.LocationValue) -> bool:
        if value.ip is None or value.port == 0:
            self.error('location error: %s' % value)
            return False
        if value.address is None or value.signature is None:
            self.error('location not signed')
            return False
        # user ID
        uid = g_facebook.identifier(string=value.id)
        if uid is None:
            self.error('user ID error: %s' % value.id)
            return False
        user = g_facebook.user(identifier=uid)
        # verify mapped address with signature
        timestamp = dmtp.TimestampValue(value=value.timestamp)
        data = value.address + timestamp.data
        if not user.verify(data=data, signature=value.signature):
            self.error('location signature not match: %s' % value)
            return False
        self.__locations[value.id] = value
        self.__locations[(value.ip, value.port)] = value
        self.info('location updated: %s' % value)
        return True

    def get_location(self, uid: str = None, source: tuple = None) -> Optional[dmtp.LocationValue]:
        if uid is None:
            return self.__locations.get(source)
        else:
            return self.__locations.get(uid)

    def process_command(self, cmd: dmtp.Command, source: tuple) -> bool:
        # noinspection PyBroadException
        try:
            return super().process_command(cmd=cmd, source=source)
        except Exception:
            traceback.print_exc()
            return False

    def process_message(self, msg: dmtp.Message, source: tuple) -> bool:
        self.info('received msg: %s' % msg)
        return True

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
