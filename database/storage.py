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

import json
import os
import time
import sys

from dimp import ID
from dimp import Barrack


def current_time() -> str:
    time_array = time.localtime()
    return time.strftime('%Y-%m-%d %H:%M:%S', time_array)


class Storage:

    root = 'C:\\tmp\\.dim' if sys.platform == 'win32' else '/tmp/.dim'

    @classmethod
    def exists(cls, path: str) -> bool:
        return os.path.exists(path)

    @classmethod
    def read_text(cls, path: str) -> str:
        if cls.exists(path):
            # reading
            with open(path, 'r') as file:
                return file.read()

    @classmethod
    def read_json(cls, path: str) -> dict:
        text = cls.read_text(path)
        if text is not None:
            return json.loads(text)

    @classmethod
    def write_text(cls, text: str, path: str) -> bool:
        directory = os.path.dirname(path)
        # make sure the dirs exists
        if not cls.exists(directory):
            os.makedirs(directory)
        # writing
        with open(path, 'w') as file:
            wrote = file.write(text)
            return wrote == len(text)

    @classmethod
    def write_json(cls, content: dict, path: str) -> bool:
        string = json.dumps(content)
        return cls.write_text(string, path)

    @classmethod
    def append_text(cls, text: str, path: str) -> bool:
        if not cls.exists(path=path):
            # new file
            return cls.write_text(text=text, path=path)
        # appending
        with open(path, 'a') as file:
            wrote = file.write(text)
            return wrote == len(text)

    @classmethod
    def remove(cls, path: str) -> bool:
        if cls.exists(path=path):
            os.remove(path)
            return True

    #
    #  Entity factory
    #
    barrack: Barrack = None

    @classmethod
    def identifier(cls, string: str) -> ID:
        if cls.barrack is None:
            return ID(string)
        return cls.barrack.identifier(string=string)

    #
    #  Log
    #
    @classmethod
    def info(cls, msg: str):
        print('[%s] Storage > %s' % (current_time(), msg))

    @classmethod
    def error(cls, msg: str):
        print('[%s] Storage ERROR > %s' % (current_time(), msg))
