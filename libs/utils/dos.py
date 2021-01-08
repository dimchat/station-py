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
    Disk Operating System
    ~~~~~~~~~~~~~~~~~~~~~

    File access
"""

import json
import os
from typing import Union, Optional, AnyStr


class File:

    def __init__(self, path: str):
        super().__init__()
        self.__path: str = path
        self.__data: AnyStr = None

    @classmethod
    def make_dirs(cls, directory: str) -> bool:
        if os.path.exists(directory):
            if os.path.isdir(directory):
                # directory exists
                return True
            else:
                raise IOError('%s exists but is not a directory!' % directory)
        else:
            os.makedirs(directory, exist_ok=True)
            return True

    def exists(self, path: str=None) -> bool:
        # param 'path' deprecated
        if path is None:
            path = self.__path
        return os.path.exists(path)

    def remove(self, path: str=None) -> bool:
        if path is None:
            path = self.__path
        if os.path.exists(path):
            os.remove(path)
            return True

    def read(self, mode: str='rb', encoding=None) -> Optional[AnyStr]:
        if self.__data is not None:
            # get data from cache
            return self.__data
        if not os.path.exists(self.__path):
            # file not found
            return None
        if not os.path.isfile(self.__path):
            # the path is not a file
            raise IOError('%s is not a file' % self.__path)
        with open(self.__path, mode=mode, encoding=encoding) as file:
            self.__data = file.read()
        return self.__data

    def write(self, data: AnyStr, mode: str='wb', encoding=None) -> bool:
        directory = os.path.dirname(self.__path)
        if not self.make_dirs(directory):
            return False
        with open(self.__path, mode=mode, encoding=encoding) as file:
            if len(data) == file.write(data):
                # OK, update cache
                self.__data = data
                return True

    def append(self, data: AnyStr, mode: str='ab', encoding=None) -> bool:
        if not os.path.exists(self.__path):
            # new file
            return self.write(data, mode=mode)
        # append to exists file
        with open(self.__path, mode=mode, encoding=encoding) as file:
            if len(data) == file.write(data):
                # OK, erase cache for next update
                self.__data = None
                return True


class TextFile(File):

    def read(self, mode: str='r', encoding='utf-8') -> Optional[str]:
        return super().read(mode=mode, encoding=encoding)

    def write(self, text: str, mode: str='w', encoding='utf-8') -> bool:
        return super().write(text, mode=mode, encoding=encoding)

    def append(self, text: str, mode: str='a', encoding='utf-8') -> bool:
        return super().append(text, mode=mode, encoding=encoding)


class JSONFile(TextFile):

    def __init__(self, path: str):
        super().__init__(path=path)
        self.__container: Union[dict, list, None] = None

    def read(self, **kwargs) -> Union[dict, list, None]:
        if self.__container is not None:
            # get content from cache
            return self.__container
        # read as text file
        text = super().read()
        if text is not None:
            # convert text string to JSON object
            self.__container = json.loads(text)
        return self.__container

    def write(self, container: Union[dict, list], **kwargs) -> bool:
        # convert JSON object to text string
        text = json.dumps(container)
        if text is None:
            raise ValueError('cannot convert to JSON string: %s' % container)
        if super().write(text):
            # OK, update cache
            self.__container = container
            return True

    def append(self, **kwargs) -> bool:
        raise AssertionError('JSON file cannot be appended')
