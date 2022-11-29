# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    WebSocket Protocol
    ~~~~~~~~~~~~~~~~~~

"""

import hashlib
import struct
from typing import Optional

from dimsdk import base64_encode, utf8_encode


class WebSocket:

    #
    #   Protocol: WebSocket Handshake
    #
    ws_magic = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    ws_prefix = b'HTTP/1.1 101 Switching Protocol\r\n' \
                b'Server: DIM-Station\r\n' \
                b'Upgrade: websocket\r\n' \
                b'Connection: Upgrade\r\n' \
                b'WebSocket-Protocol: DIMP\r\n' \
                b'Sec-WebSocket-Accept: '
    ws_suffix = b'\r\n\r\n'

    @classmethod
    def handshake(cls, stream: bytes) -> Optional[bytes]:
        pos1 = stream.find(b'Sec-WebSocket-Key:')
        if pos1 < 0:
            return None
        pos1 += len('Sec-WebSocket-Key:')
        pos2 = stream.find(b'\r\n', pos1)
        if pos2 < 0:
            return None
        key = stream[pos1:pos2].strip()
        sec = hashlib.sha1(key + cls.ws_magic).digest()
        sec = base64_encode(data=sec)
        sec = utf8_encode(string=sec)
        return cls.ws_prefix + sec + cls.ws_suffix

    @classmethod
    def is_handshake(cls, stream: bytes) -> bool:
        return stream.find(b'Sec-WebSocket-Key') > 0

    """
        RFC: https://tools.ietf.org/html/rfc6455#section-5.2

         0                   1                   2                   3
         0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        +-+-+-+-+-------+-+-------------+-------------------------------+
        |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
        |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
        |N|V|V|V|       |S|             |   (if payload len==126/127)   |
        | |1|2|3|       |K|             |                               |
        +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
        |     Extended payload length continued, if payload len == 127  |
        + - - - - - - - - - - - - - - - +-------------------------------+
        |                               |Masking-key, if MASK set to 1  |
        +-------------------------------+-------------------------------+
        | Masking-key (continued)       |          Payload Data         |
        +-------------------------------- - - - - - - - - - - - - - - - +
        :                     Payload Data continued ...                :
        + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        |                     Payload Data continued ...                |
        +---------------------------------------------------------------+
    """
    @classmethod
    def parse(cls, stream: bytes) -> (bytes, bytes):
        """
        Parse WebSocket data stream

        :param stream: data stream
        :return: (payload, remaining_data)
        """
        stream_len = len(stream)
        if stream_len < 2:
            return None, stream
        data = b''
        pos = 0
        while True:
            if stream_len < pos + 2:
                # self.info('incomplete ws package for op code: %d' % stream_len)
                return None, stream
            # 1. check whether a continuation frame
            ch0 = stream[pos+0]
            # fin: indicates that this is the final fragment in a message.
            # op: 0 - denotes a continuation frame
            fin = ch0 >> 7
            op = ch0 & 0x0F
            # 2. get payload length
            ch1 = stream[pos+1]
            mask = ch1 >> 7
            msg_len = ch1 & 0x7F
            if msg_len == 126:
                if stream_len < pos + 4:
                    # self.info('incomplete ws package for msg len: %d' % stream_len)
                    return None, stream
                b2 = stream[pos+2]
                b3 = stream[pos+3]
                msg_len = (b2 << 8) | b3
                pos += 4
            elif msg_len == 127:
                if stream_len < pos + 10:
                    # self.info('incomplete ws package for msg len: %d' % stream_len)
                    return None, stream
                b2 = stream[pos+2]
                b3 = stream[pos+3]
                b4 = stream[pos+4]
                b5 = stream[pos+5]
                b6 = stream[pos+6]
                b7 = stream[pos+7]
                b8 = stream[pos+8]
                b9 = stream[pos+9]
                msg_len = b2 << 56 | b3 << 48 | b4 << 40 | b5 << 32 | b6 << 24 | b7 << 16 | b8 << 8 | b9
                pos += 10
            else:
                pos += 2
            # 3. get masking-key
            if mask == 1:
                if stream_len < pos + 4:
                    # self.info('incomplete ws package for mask: %d' % stream_len)
                    return None, stream
                mask = stream[pos:pos+4]
                pos += 4
            else:
                mask = None
            # 4. get payload
            if stream_len < pos + msg_len:
                # self.info('incomplete ws package for payload: %d' % stream_len)
                return None, stream
            payload = stream[pos:pos+msg_len]
            pos += msg_len
            if mask is None:
                content = payload
            else:
                content = bytearray()
                for i, d in enumerate(payload):
                    content.append(d ^ mask[i % 4])
            # 5. check op_code
            if op == 0:
                data += content
            elif op == 1:
                # TEXT
                data += content
            elif op == 2:
                # BINARY
                data += content
            elif op == 8:
                # TODO: CLOSE
                pass
            elif op == 9:
                # TODO: PING
                pass
            elif op == 10:
                # TODO: PONG
                pass
            else:
                # self.error('ws op error: %d => %s' % (op, stream))
                return None, b''
            # 6. check final fragment
            if fin == 1 or op == 0:
                # cut the received package(s) and return the remaining
                stream = stream[pos:]
                break
        # self.info('received ws payload len: %d' % len(data))
        return data, stream

    @classmethod
    def pack(cls, payload: bytes) -> bytes:
        head = struct.pack('B', 129)
        msg_len = len(payload)
        if msg_len < 126:
            head += struct.pack('B', msg_len)
        elif msg_len <= (2 ** 16 - 1):
            head += struct.pack('!BH', 126, msg_len)
        elif msg_len <= (2 ** 64 - 1):
            head += struct.pack('!BQ', 127, msg_len)
        else:
            raise ValueError('message is too long: %d' % msg_len)
        return head + payload
