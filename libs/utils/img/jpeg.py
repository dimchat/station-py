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

from .api import Type, BaseImage, BaseScanner


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
    # APPn E1-EF # Reserved for application use

    # JPGn F0-FD # Reserved for JPEG extension
    COM = 0xFE   # Comment


class Segment(Data):
    """
        JPEG Segment
        ~~~~~~~~~~~~

        format: MarkCode + Length + Body
                len(MarkCode) == 2
                len(Length) == 2
                Length = len(Body) + 2
    """

    def __init__(self, data: ByteArray, mark: int, body: ByteArray):
        super().__init__(buffer=data.buffer, offset=data.offset, size=data.size)
        self.__mark = mark
        self.__body = body

    def __str__(self) -> str:
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s:FF%X| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.mark, self.offset, self.size, start, end)

    def __repr__(self) -> str:
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

    @classmethod
    def new(cls, mark: int, body: ByteArray):  # -> Segment
        mark_code = 0xFF00 + (mark & 0x00FF)
        mark_code = Convert.uint16data_from_value(value=mark_code)
        length = Convert.uint16data_from_value(value=(2 + body.size))
        # MarkCode + Length + Body
        data = mark_code.concat(other=length).concat(other=body)
        return cls(data=data, mark=mark, body=body)

    @classmethod
    def parse(cls, data: ByteArray, start: int = 0):  # -> Segment:
        assert (start + 2) <= data.size, 'out of range: %d, %d' % (start, data.size)
        mark = data.get_byte(index=(start + 1))
        if mark in [0xD8, 0xD9]:
            end = start + 2
        else:
            assert (start + 4) <= data.size, 'out of range: %d, %d' % (start, data.size)
            # get Length in range [start + 2, start + 4)
            length = Convert.int16_from_data(data=data, start=(start + 2))
            end = start + 2 + length
            assert end <= data.size, 'out of range: %d, %d' % (end, data.size)
        if 0 < start or end < data.size:
            data = data.slice(start=start, end=end)
        # MarkCode + Length + Body
        body = data.slice(start=4)
        return cls(data=data, mark=mark, body=body)


class ImageSegment(Segment):
    """ image data between SOS and EOI """

    def __init__(self, data: ByteArray):
        super().__init__(data=data, mark=0, body=data)

    def __str__(self) -> str:
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.offset, self.size, start, end)

    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.offset, self.size, start, end)


class JPEG(BaseImage):
    """ JPEG Image
        ~~~~~~~~~~
    """

    def __init__(self, data: ByteArray, width: int, height: int):
        super().__init__(data=data, width=width, height=height, image_type=Type.JPEG)


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
        return pos - start + len(EOI_BUF)
    else:
        # FIXME: no 'EOI' segment?
        return data.size


class JPEGScanner(BaseScanner[Segment]):
    """ Image scanner for JPEG """

    @classmethod
    def check(cls, data: ByteArray) -> bool:
        """ check whether JPEG data """
        return seek_start(data=data) != -1

    # Override
    def _prepare(self, data: ByteArray) -> bool:
        if not super()._prepare(data=data):
            return False
        # seeking start & end chunks
        offset = seek_start(data=data)
        if offset < 0:
            return False  # not a JPEG file
        else:
            self._info['type'] = Type.JPEG
        bounds = seek_end(data=data)
        if bounds > offset:
            self._data = data
            self._offset = offset
            self._bounds = bounds
            return True

    # Override
    def _next(self) -> Optional[Segment]:
        """ next segment """
        data = self._data
        offset = self._offset
        bounds = self._bounds
        if offset == bounds:
            # finished
            return None
        assert offset < bounds, 'out of range: %d, %d' % (offset, bounds)
        chunk = self.__create_chunk(data=data, start=offset)
        self._offset += chunk.size
        return chunk

    def __create_chunk(self, data: ByteArray, start: int) -> Segment:
        if data.get_byte(index=start) == 0xFF:
            # normal segment
            start = self.__skip_ffs(start=start)
            self._offset = start
            return self._create_segment(data=data, start=start)
        else:
            # data segment
            end = self.__seek_eoi(start=start)
            data = data.slice(start=start, end=end)
            return self._create_image_data_segment(data=data)

    def __skip_ffs(self, start: int) -> int:
        """ skip 'FF..FF' for next segment """
        data = self._data
        bounds = self._bounds
        pos = start + 1
        while pos < bounds and data.get_byte(index=pos) == 0xFF:
            pos += 1
        assert pos < bounds, 'out of range: %d, %d' % (pos, bounds)
        return pos - 1  # back to last 'FF'

    def __seek_eoi(self, start: int) -> int:
        """ seek for EOI segment """
        data = self._data
        bounds = self._bounds
        assert start + 2 <= bounds, 'out of range: %d, %d' % (start, bounds)
        c1 = data.get_byte(index=(bounds - 2))
        c2 = data.get_byte(index=(bounds - 1))
        if c1 == 0xFF and c2 == 0xD9:
            return bounds - 2  # EOI
        else:
            return bounds  # EOI lost?

    # noinspection PyMethodMayBeStatic
    def _create_segment(self, data: ByteArray, start: int) -> Segment:
        """ create segment with data from start position """
        return Segment.parse(data=data, start=start)

    # noinspection PyMethodMayBeStatic
    def _create_image_data_segment(self, data: ByteArray):
        """ create image data segment within range [start, end) """
        return ImageSegment(data=data)

    # Override
    def _analyse(self, segment: Segment) -> bool:
        """ analyse each segment """
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
        elif mark == MarkCode.SOI:
            self._analyse_soi(segment=segment)
        elif mark == MarkCode.EOI:
            self._analyse_eoi(segment=segment)
        elif isinstance(segment, ImageSegment):
            self._analyse_image_data(segment=segment)
        else:
            # let sub class to analyse other segment
            return False
        # analysed
        return True

    def _analyse_app_0(self, segment: Segment):
        """ Application 0: E0 """
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
        """ Application 1~15: E1~EF """
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

    def _analyse_soi(self, segment: Segment):
        """ Start Of Image: D8 """
        pass

    def _analyse_eoi(self, segment: Segment):
        """ End Of Image: D9 """
        pass

    def _analyse_image_data(self, segment: ImageSegment):
        """ Image Data """
        pass
