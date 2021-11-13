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

"""
    Image API
    ~~~~~~~~~

"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

from udp.ba import ByteArray, Data


class Image(ABC):

    BMP = 'bmp'
    GIF = 'gif'
    PNG = 'png'
    JPEG = 'jpeg'

    @property
    def type(self) -> str:
        """ image type """
        raise NotImplemented

    @property
    def width(self) -> int:
        """ image width in pixel """
        raise NotImplemented

    @property
    def height(self) -> int:
        """ image height in pixel """
        raise NotImplemented


class ImageScanner(ABC):

    @abstractmethod
    def scan(self, data: ByteArray) -> Optional[Image]:
        """ scanning """
        raise NotImplemented


class BaseImage(Data, Image, ABC):

    def __init__(self, data: ByteArray, width: int, height: int):
        super().__init__(buffer=data.buffer, offset=data.offset, size=data.size)
        self.__width = width
        self.__height = height

    @property  # Override
    def width(self) -> int:
        return self.__width

    @property  # Override
    def height(self) -> int:
        return self.__height


C = TypeVar('C')


class BaseScanner(ImageScanner, Generic[C], ABC):

    def __init__(self):
        super().__init__()
        self._data: Optional[ByteArray] = None
        self._offset = -1
        self._bounds = -1
        self._info = {}

    def _prepare(self, data: ByteArray) -> bool:
        """ clear before scanning """
        self._data = data
        self._offset = -1
        self._bounds = -1
        self._info.clear()
        return True

    @abstractmethod
    def _next(self) -> Optional[C]:
        """ next chunk """
        raise NotImplemented

    @abstractmethod
    def _analyse(self, chunk: C) -> bool:
        """ analyse each chunk """
        raise NotImplemented

    @abstractmethod
    def _create_image(self) -> Image:
        """ create image after scanned """
        raise NotImplemented

    # Override
    def scan(self, data: ByteArray) -> Optional[Image]:
        if not self._prepare(data=data):
            # image data error
            return None
        # start to parse PNG data
        while True:
            chunk = self._next()
            if chunk is None:
                break
            self._analyse(chunk)
        # finished scanning, create image
        return self._create_image()
