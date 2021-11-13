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
from typing import Optional

from udp.ba import ByteArray, Data, Convert

from .api import Image, BaseImage, BaseScanner


class MarkCode(IntEnum):
    """ Mark Code of Segments """

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

    def __str__(self):
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s:FF%X| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.mark, self.offset, self.size, start, end)

    def __repr__(self):
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s:FF%X| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.mark, self.offset, self.size, start, end)

    @property
    def mark(self) -> int:
        """ Mark Code """
        return self.__mark

    @property
    def body(self) -> ByteArray:
        """ Segment Data """
        return self.__body


class JPEG(BaseImage):
    """ JPEG Image
        ~~~~~~~~~~
    """

    @property  # Override
    def type(self) -> str:
        return Image.JPEG


SOI_BUF = b'\xFF\xD8'
EOI_BUF = b'\xFF\xD9'


def seek_start(data: ByteArray) -> int:
    """ seek SOI """
    if data.slice(start=0, end=2) == SOI_BUF:
        return 0
    else:
        return -1


def seek_end(data: ByteArray) -> int:
    """ seek EOI """
    buffer = data.buffer
    start = data.offset
    end = data.offset + data.size
    pos = buffer.rfind(EOI_BUF, start, end)
    if pos > start:
        return pos - start
    else:
        # FIXME: no 'EOI' segment?
        return data.size


class JPEGScanner(BaseScanner[Segment]):
    """ Image scanner for JPEG """

    @classmethod
    def check(cls, data: ByteArray) -> bool:
        return seek_start(data=data) == 0

    # Override
    def _prepare(self, data: ByteArray) -> bool:
        if not super()._prepare(data=data):
            return False
        # seeking start & end chunks
        offset = seek_start(data=data)
        if offset < 0:
            return False  # not a PNG file
        else:
            offset += 2  # skip SOI
        bounds = seek_end(data=data)
        if bounds > offset:
            self._data = data
            self._offset = offset
            self._bounds = bounds
            return True

    # Override
    def _create_image(self) -> Image:
        """ create JPEG image """
        width = self._info.get('width')
        height = self._info.get('height')
        return JPEG(data=self._data, width=width, height=height)

    # Override
    def _next(self) -> Optional[Segment]:
        """ next segment """
        data = self._data
        offset = self._offset
        bounds = self._bounds
        assert offset < bounds, 'out of range: %d, %d' % (offset, bounds)
        if data.get_byte(index=offset) != 0xFF:
            # data error?
            # or after SOS
            return None
        # skip all 'FF'
        offset += 1
        while offset < bounds and data.get_byte(index=offset) == 0xFF:
            offset += 1
        offset += 1  # skip 'mark'
        assert offset + 2 <= bounds, 'out of range: %d, %d' % (offset, bounds)
        # get body size within range [2, 4)
        size = Convert.int16_from_data(data=data, start=offset)
        end = offset + size
        assert end <= bounds, 'out of range: %d, %d' % (end, bounds)
        self._offset = end  # move to tail of current segment
        # include the mark
        offset -= 2
        size += 2
        return self._create_segment(offset=offset, size=size)

    def _create_segment(self, offset: int, size: int) -> Segment:
        """ create segment with data range [offset, offset+size) """
        data = self._data
        data = data.slice(start=offset, end=(offset+size))
        # assert isinstance(data, ByteArray), 'data error: %s' % data
        mark = data.get_byte(index=1)
        body = data.slice(start=4)
        return Segment(data=data, mark=mark, body=body)

    # Override
    def _analyse(self, segment: Segment) -> bool:
        mark = segment.mark
        if mark == MarkCode.APP0:
            self._analyse_app_0(segment=segment)
        elif 0xE0 < mark <= 0xEF:
            self._analyse_app_n(segment=segment)
        elif mark == MarkCode.SOF0:
            self._analyse_sof_0(segment=segment)
        elif mark == MarkCode.DHT:
            self._analyse_dht(segment=segment)
        elif mark == MarkCode.DQT:
            self._analyse_dqt(segment=segment)
        elif mark == MarkCode.DRI:
            self._analyse_dri(segment=segment)
        elif mark == MarkCode.SOS:
            self._analyse_sos(segment=segment)
        else:
            # let sub class to analyse other segment
            return False
        # analysed
        return True

    def _analyse_app_0(self, segment: Segment):
        """ Application 0 """
        body = segment.body
        assert body.size >= 14, 'APP0 error: %s' % segment
        magic_code = body.slice(start=0, end=5)
        assert magic_code == b'JFIF\0', 'magic code error: %s' % magic_code
        unit = body.get_byte(index=7)
        assert 0 <= unit <= 2, 'unit error: %d' % unit
        x = Convert.int16_from_data(data=body, start=8)
        y = Convert.int16_from_data(data=body, start=10)
        self._info['dpi.x'] = x
        self._info['dpi.y'] = y

    def _analyse_app_n(self, segment: Segment):
        """ Application 1~15 """
        pass

    def _analyse_sof_0(self, segment: Segment):
        """ Start Of Frame: C0 """
        pass
        body = segment.body
        assert body.size >= 15, 'SOF0 error: %s' % segment
        d = body.get_byte(index=0)
        h = Convert.int16_from_data(data=body, start=1)
        w = Convert.int16_from_data(data=body, start=3)
        self._info['width'] = w
        self._info['height'] = h
        self._info['depth'] = d

    def _analyse_dht(self, segment: Segment):
        """ Define Huffman Table: C4 """
        pass

    def _analyse_dqt(self, segment: Segment):
        """ Define Quantization Table: DB """
        pass

    def _analyse_dri(self, segment: Segment):
        """ Define Restart Interval: DD """
        pass

    def _analyse_sos(self, segment: Segment):
        """ Start Of Scan: DA """
        pass
