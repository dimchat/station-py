# -*- coding: utf-8 -*-
#
#   JPEG: Joint Photographic Experts Group
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
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

from enum import IntEnum

from udp.ba import ByteArray, Data, MutableData
from udp.ba import Convert

from .log import Logging


class MarkCode(IntEnum):

    TEM = 0x01   # For temporary use in arithmetic coding
    # RESn 02-BF # Reserved

    SOF0 = 0xC0  # Start Of Frame
    # SOFn C0-C3 # Start Of Frame markers, non-hierarchical Huffman coding
    DHT = 0xC4   # Define Huffman Table
    # SOFn C5-C7 # Start Of Frame markers, hierarchical Huffman coding
    JPG = 0xC8   # Reserved for JPEG extensions
    # SOFn C9-CB # Start Of Frame markers, non-hierarchical arithmetic coding
    DAC = 0xCC   # Define Arithmetic Conditioning table
    # SOFn CD-CF # Start Of Frame markers, hierarchical arithmetic coding

    # RSTm D0-D7 # Restart interval termination
    SOI = 0xD8   # Start Of Image
    EOI = 0xD9   # End of Image
    SOS = 0xDA   # Start Of Scan
    DQT = 0xDB   # Define Quantization Table
    DNL = 0xDC   # Define Number of Lines
    DRI = 0xDD   # Define Restart Interval
    DHP = 0xDE   # Define Hierarchical Progression
    EXP = 0xDF   # Expand reference image(s)

    APP0 = 0xE0  # Application 0
    # APPn E0-EF # Reserved for application use

    # JPGn F0-FD # Reserved for JPEG extension
    COM = 0xFE   # Comment


class Segment(Data):
    """ Mark + Length + Body """

    def __init__(self, data: ByteArray, mark: int, body: ByteArray):
        super().__init__(buffer=data.buffer, offset=data.offset, size=data.size)
        self.__mark = mark
        self.__body = body

    @property
    def mark(self) -> int:
        """ mark code """
        return self.__mark

    @property
    def body(self) -> ByteArray:
        """ segment data """
        return self.__body

    @property
    def start(self) -> int:
        """ start position (start of mark code) """
        return self.offset

    @property
    def end(self) -> int:
        """ end position (end of body) """
        return self.offset + self.size


class JPEG(MutableData, Logging):

    def __init__(self, data: ByteArray):
        buffer = data.buffer
        if not isinstance(buffer, bytearray):
            buffer = bytearray(buffer)
        start = data.offset
        end = start + data.size
        # seeking SOI
        start = buffer.find(b'\xFF\xD8', start, end)
        assert start >= 0, 'SOI not found'
        # seeking EOI
        end = buffer.rfind(b'\xFF\xD9', start, end)
        assert start < end, 'EOI not found'
        end += 2
        # create with range: [start, end)
        super().__init__(buffer=buffer, offset=start, size=(end-start))
        self._pos = -1
        self._bounds = -1
        self._info = {}

    def _prepare(self):
        self._pos = self.offset + 2
        self._bounds = self.offset + self.size - 2
        self._info.clear()

    def get_info(self, key: str):
        return self._info.get(key)

    def _set_info(self, key: str, value):
        self._info[key] = value

    @property
    def width(self) -> int:
        x = self.get_info(key='width')
        if x is None:
            x = 0
        return x

    @property
    def height(self) -> int:
        y = self.get_info(key='height')
        if y is None:
            y = 0
        return y

    def _next_segment(self) -> (int, bytes, int, int):
        """ Seek for next segment """
        buffer = self.buffer
        pos = self._pos
        bounds = self._bounds
        assert 0 < pos < bounds, 'out of range: %d, %d' % (pos, bounds)
        if buffer[pos] != 0xFF:
            # data error?
            # or after SOS
            return None
        # skip 'FF'
        pos += 1
        while pos < bounds and buffer[pos] == 0xFF:
            pos += 1
        assert pos < bounds, 'out of range: %d, %d' % (pos, bounds)
        # get 'mark'
        mark = buffer[pos]
        pos += 1  # skip 'mark'
        # get body size
        size = Convert.int16_from_data(data=buffer, start=pos)
        end = pos + size
        assert end < bounds, 'out of range: %d, %d' % (end, bounds)
        # get 'body' within 'segment'
        body = Data(buffer=buffer, offset=(pos+2), size=(size-2))
        data = Data(buffer=buffer, offset=(pos-2), size=(size+2))
        self._pos = end  # move forward
        return Segment(data=data, mark=mark, body=body)

    def analyse(self):
        self._prepare()
        while True:
            segment = self._next_segment()
            if segment is None:
                self.debug('stopped')
                break
            try:
                self._analyse(segment=segment)
            except Exception as error:
                self.error('failed to analyse %x: %s' % (segment.mark, error))

    def _analyse(self, segment: Segment) -> bool:
        mark = segment.mark
        if mark == MarkCode.APP0:
            self._analyse_app_0(segment=segment)
        elif 0xE0 < mark <= 0xEF:
            self._analyse_app_n(segment=segment)
        elif mark == MarkCode.DQT:
            self._analyse_dqt(segment=segment)
        elif mark == MarkCode.SOF0:
            self._analyse_sof_0(segment=segment)
        elif mark == MarkCode.DHT:
            self._analyse_dht(segment=segment)
        elif mark == MarkCode.SOS:
            self._analyse_sos(segment=segment)
        else:
            self.debug('unknown, mark: %x, offset: %x' % (mark, segment.offset))
            return False
        # analysed
        return True

    def _analyse_app_0(self, segment: Segment):
        """ Application 0 """
        self.debug('APP0, mark: %x, offset: %x' % (segment.mark, segment.offset))
        body = segment.body
        assert body.size >= 14, 'APP0 error: %s' % segment
        magic_code = body.slice(start=0, end=5)
        assert magic_code == b'JFIF\0', 'magic code error: %s' % magic_code
        unit = body.get_byte(index=7)
        assert 0 <= unit <= 2, 'unit error: %d' % unit
        x = Convert.int16_from_data(data=body, start=8)
        y = Convert.int16_from_data(data=body, start=10)
        self._set_info(key='dpi.x', value=x)
        self._set_info(key='dpi.y', value=y)
        self.debug('----> DPI: %d x %d, unit: %d' % (x, y, unit))

    def _analyse_app_n(self, segment: Segment):
        """ Application 1~15 """
        self.debug('APPn, mark: %x, offset: %x' % (segment.mark, segment.offset))

    def _analyse_dqt(self, segment: Segment):
        """ Define Quantization Table: DB """
        self.debug('DQT,  mark: %x, offset: %x' % (segment.mark, segment.offset))

    def _analyse_sof_0(self, segment: Segment):
        """ Start Of Frame: C0 """
        self.debug('SOF0, mark: %x, offset: %x' % (segment.mark, segment.offset))
        body = segment.body
        assert body.size >= 15, 'SOF0 error: %s' % segment
        depth = body.get_byte(index=0)
        h = Convert.int16_from_data(data=body, start=1)
        w = Convert.int16_from_data(data=body, start=3)
        self._set_info(key='height', value=h)
        self._set_info(key='width', value=w)
        self.debug('----> size: %d x %d, depth: %d' % (w, h, depth))

    def _analyse_dht(self, segment: Segment):
        """ Define Huffman Table: C4 """
        self.debug('DHT,  mark: %x, offset: %x' % (segment.mark, segment.offset))

    def _analyse_sos(self, segment: Segment):
        """ Start Of Scan: DA """
        self.debug('SOS,  mark: %x, offset: %x' % (segment.mark, segment.offset))
