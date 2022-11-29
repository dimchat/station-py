# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from startrek import Hub, Channel, Connection, ConnectionDelegate
from startrek import ConnectionState, ConnectionStateMachine
from startrek import BaseChannel, ChannelReader, ChannelWriter
from startrek import BaseHub, BaseConnection, ActiveConnection

from startrek import Ship, Arrival, Departure, DeparturePriority
from startrek import Docker, DockerStatus, DockerDelegate, Gate
from startrek import ArrivalShip, ArrivalHall, DepartureShip, DepartureHall
from startrek import Dock, LockedDock, StarDocker, StarGate

from tcp import PlainArrival, PlainDeparture, PlainDocker
from tcp import StreamChannel, StreamHub
from tcp import ServerHub as TCPServerHub, ClientHub as TCPClientHub

from udp import PackageArrival, PackageDeparture, PackageDocker
from udp import PacketChannel, PacketHub
from udp import ServerHub as UDPServerHub, ClientHub as UDPClientHub

from .protocol import WebSocket, NetMsg, NetMsgHead, NetMsgSeq

from .ws import WSArrival, WSDeparture, WSDocker
from .mars import MarsStreamArrival, MarsStreamDeparture, MarsStreamDocker
from .mtp import MTPStreamArrival, MTPStreamDeparture, MTPStreamDocker
from .gate import CommonGate, TCPServerGate, TCPClientGate, UDPServerGate, UDPClientGate

from .queue import MessageWrapper, MessageQueue
from .gatekeeper import GateKeeper


__all__ = [

    #
    #   StarTrek
    #
    'Hub', 'Channel', 'Connection', 'ConnectionDelegate',
    'ConnectionState', 'ConnectionStateMachine',
    'BaseChannel', 'ChannelReader', 'ChannelWriter',
    'BaseHub', 'BaseConnection', 'ActiveConnection',

    'Ship', 'Arrival', 'Departure', 'DeparturePriority',
    'Docker', 'DockerStatus', 'DockerDelegate', 'Gate',
    'ArrivalShip', 'ArrivalHall', 'DepartureShip', 'DepartureHall',
    'Dock', 'LockedDock', 'StarDocker', 'StarGate',

    #
    #   TCP
    #
    'PlainArrival', 'PlainDeparture', 'PlainDocker',
    'StreamChannel', 'StreamHub', 'TCPServerHub', 'TCPClientHub',

    #
    #   UDP
    #
    'PackageArrival', 'PackageDeparture', 'PackageDocker',
    'PacketChannel', 'PacketHub', 'UDPServerHub', 'UDPClientHub',

    #
    #   Protocol
    #
    'WebSocket', 'NetMsg', 'NetMsgHead', 'NetMsgSeq',

    #
    #   Network
    #
    'WSArrival', 'WSDeparture', 'WSDocker',
    'MarsStreamArrival', 'MarsStreamDeparture', 'MarsStreamDocker',
    'MTPStreamArrival', 'MTPStreamDeparture', 'MTPStreamDocker',
    'CommonGate', 'TCPServerGate', 'TCPClientGate', 'UDPServerGate', 'UDPClientGate',
    'MessageWrapper', 'MessageQueue',
    'GateKeeper',
]
