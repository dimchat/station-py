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

import time

from dimsdk.dos import File, TextFile, JSONFile


def current_time() -> str:
    time_array = time.localtime()
    return time.strftime('%Y-%m-%d %H:%M:%S', time_array)


class Storage:

    root = '/tmp/.dim'

    @classmethod
    def exists(cls, path: str) -> bool:
        return File(path=path).exists(path=path)

    @classmethod
    def read_text(cls, path: str) -> str:
        return TextFile(path=path).read()

    @classmethod
    def read_json(cls, path: str) -> dict:
        return JSONFile(path=path).read()

    @classmethod
    def write_text(cls, text: str, path: str) -> bool:
        return TextFile(path=path).write(text=text)

    @classmethod
    def write_json(cls, container: dict, path: str) -> bool:
        return JSONFile(path=path).write(container=container)

    @classmethod
    def append_text(cls, text: str, path: str) -> bool:
        return TextFile(path=path).append(text=text)

    @classmethod
    def remove(cls, path: str) -> bool:
        return File(path=path).remove()

    #
    #  Log
    #
    @classmethod
    def info(cls, msg: str):
        print('[%s] Storage > %s' % (current_time(), msg))

    @classmethod
    def error(cls, msg: str):
        print('[%s] ERROR - Storage > %s' % (current_time(), msg))
