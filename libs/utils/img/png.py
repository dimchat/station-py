# -*- coding: utf-8 -*-
#
#   PNG: Portable Network Graphics
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

import zlib
from typing import Optional

from dimp import utf8_encode, utf8_decode
from udp.ba import ByteArray, Data, Convert

from .api import Image, BaseImage, BaseScanner


class TypeCode:
    """ Type Code of Chunks """

    #
    #   Critical Chunks
    #
    IHDR = 'IHDR'  # header chunk
    PLTE = 'PLTE'  # palette chunk
    IDAT = 'IDAT'  # image data chunk
    IEND = 'IEND'  # image trailer chunk

    #
    #   Ancillary Chunks
    #
    cHRM = 'cHRM'  # primary chromaticities and white point
    gAMA = 'gAMA'  # image gamma
    sBIT = 'sBIT'  # significant bits
    bKGD = 'bKGD'  # background color
    hIST = 'hIST'  # image histogram
    tRNS = 'tRNS'  # transparency
    oFFs = 'oFFs'
    pHYs = 'pHYs'  # physical pixel dimensions
    sCAL = 'sCAL'
    tIME = 'tIME'  # image last-modification time
    tEXt = 'tEXt'  # textual data
    zTXt = 'zTXt'  # compressed textual data
    fRAc = 'fRAc'
    gIFg = 'gIFg'
    gIFt = 'gIFt'
    gIFx = 'gIFx'

    @classmethod
    def is_critical(cls, code: str):
        assert not cls.is_safe_copy(code=code), 'critical chunks are always not safe to copy'
        return ord(code[0]) & 0x20 == 0  # ..0. ....

    @classmethod
    def is_ancillary(cls, code: str):
        return ord(code[0]) & 0x20 != 0  # ..1. ....

    @classmethod
    def is_public(cls, code: str):
        return ord(code[1]) & 0x20 == 0  # ..0. ....

    @classmethod
    def is_private(cls, code: str):
        return ord(code[1]) & 0x20 != 0  # ..1. ....

    @classmethod
    def is_valid(cls, code: str):
        # reserved bit
        return ord(code[2]) & 0x20 == 0  # ..0. ....

    @classmethod
    def is_safe_copy(cls, code: str):
        return ord(code[3]) & 0x20 != 0  # ..1. ....


class Chunk(Data):
    """ BodyLength + TypeCode + Body + CRC """

    def __init__(self, data: ByteArray, code: str, body: ByteArray, crc: ByteArray):
        super().__init__(buffer=data.buffer, offset=data.offset, size=data.size)
        self.__code = code
        self.__body = body
        self.__crc = crc

    def __str__(self):
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s:%s| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.code, self.offset, self.size, start, end)

    def __repr__(self):
        clazz = self.__class__.__name__
        start = self.offset
        end = self.offset + self.size
        return '<%s:%s| offset=0x%08x +%d, [%d, %d) />' % (clazz, self.code, self.offset, self.size, start, end)

    @property
    def code(self) -> str:
        """ Chunk Type Code """
        return self.__code

    @property
    def body(self) -> ByteArray:
        """ Chunk Data """
        return self.__body

    @property
    def crc(self) -> ByteArray:
        """ Cyclic Redundancy Check """
        return self.__crc

    @classmethod
    def new(cls, code: str, body: ByteArray):
        length = Convert.uint32data_from_value(value=body.size)
        type_code = Data(buffer=utf8_encode(string=code))
        # crc(code + body)
        block = type_code.concat(body)
        crc = zlib.crc32(block.get_bytes())
        crc = Convert.uint32data_from_value(value=crc)
        # BodyLength + TypeCode + Body + CRC
        data = length.concat(other=block).concat(other=crc)
        return cls(data=data, code=code, body=body, crc=crc)


class PNG(BaseImage):
    """ PNG Image
        ~~~~~~~~~
    """

    @property  # Override
    def type(self) -> str:
        return Image.PNG


MAGIC_CODE = b'\x89PNG\x0D\x0A\x1A\x0A'
IEND_BUF = b'\x00\x00\x00\x00IEND\xAE\x42\x60\x82'


def seek_start(data: ByteArray) -> int:
    """ seek start chunk """
    if data.slice(start=0, end=8) == MAGIC_CODE:
        return 8
    else:
        return -1


def seek_end(data: ByteArray) -> int:
    """ seek end chunk """
    buffer = data.buffer
    start = data.offset
    end = data.offset + data.size
    pos = buffer.rfind(IEND_BUF, start, end)
    print('[PNG] end: %d, size: %d, %d' % (pos, data.size, len(buffer)))
    if pos > start:
        return pos - start
    else:
        # FIXME: no 'IEND' chunk?
        return data.size


class PNGScanner(BaseScanner[Chunk]):
    """ Image scanner for PNG """

    @classmethod
    def check(cls, data: ByteArray) -> bool:
        return seek_start(data=data) == 8

    # Override
    def _prepare(self, data: ByteArray) -> bool:
        if not super()._prepare(data=data):
            return False
        # seeking start & end chunks
        offset = seek_start(data=data)
        if offset < 0:
            return False  # not a PNG file
        bounds = seek_end(data=data)
        if bounds > offset:
            self._offset = offset
            self._bounds = bounds
            return True

    # Override
    def _create_image(self) -> Image:
        """ create PNG image """
        width = self._info.get('width')
        height = self._info.get('height')
        return PNG(data=self._data, width=width, height=height)

    # Override
    def _next(self) -> Optional[Chunk]:
        """ next chunk """
        data = self._data
        offset = self._offset
        bounds = self._bounds
        if offset >= bounds:
            # reach the end
            return None
        # get body length within range [0, 4)
        body_len = Convert.int32_from_data(data=data, start=offset)
        # BodyLength + TypeCode + Body + CRC
        size = 4 + 4 + body_len + 4
        end = offset + size
        assert end <= bounds, 'out of range: %d, %d, %d' % (size, end, bounds)
        self._offset = end  # move to tail of current chunk
        return self._create_chunk(offset=offset, size=size)

    def _create_chunk(self, offset: int, size: int):
        """ create chunk with data range [offset, offset+size) """
        data = self._data
        data = data.slice(start=offset, end=(offset+size))
        # assert isinstance(data, ByteArray), 'data error: %s' % data
        code = data.slice(start=4, end=8)
        # assert isinstance(code, ByteArray), 'data error: %s' % data
        code = utf8_decode(data=code.get_bytes())
        body = data.slice(start=8, end=-4)
        crc = data.slice(start=-4)
        return Chunk(data=data, code=code, body=body, crc=crc)

    # Override
    def _analyse(self, chunk: Chunk) -> bool:
        """ analyse each chunk """
        code = chunk.code
        if code == TypeCode.IHDR:
            self._analyse_ihdr(chunk=chunk)
            return True
        elif code == TypeCode.PLTE:
            self._analyse_plte(chunk=chunk)
            return True
        elif code == TypeCode.IDAT:
            self._analyse_idat(chunk=chunk)
            return True
        elif code == TypeCode.IEND:
            self._analyse_iend(chunk=chunk)
            return True

    def _analyse_ihdr(self, chunk: Chunk):
        """ IHDR: header chunk """
        body = chunk.body
        w = Convert.int32_from_data(data=body, start=0)
        h = Convert.int32_from_data(data=body, start=4)
        d = body.get_byte(index=8)
        self._info['width'] = w
        self._info['height'] = h
        self._info['depth'] = d

    def _analyse_plte(self, chunk: Chunk):
        """ PLTE: palette chunk """
        pass

    def _analyse_idat(self, chunk: Chunk):
        """ IDAT: image data chunk """
        pass

    def _analyse_iend(self, chunk: Chunk):
        """ IEND: image trailer chunk """
        pass
