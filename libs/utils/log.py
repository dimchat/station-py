#! /usr/bin/env python
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
    Log Util
    ~~~~~~~~
"""
import time


def current_time() -> str:
    time_array = time.localtime()
    return time.strftime('%Y-%m-%d %H:%M:%S', time_array)


class Log:

    DEBUG = 0
    DEVELOP = 1
    RELEASE = 2

    LEVEL = DEVELOP

    @classmethod
    def debug(cls, msg: str):
        if cls.LEVEL > cls.DEBUG:
            return None
        print('[%s] DEBUG - %s' % (current_time(), msg))

    @classmethod
    def info(cls, msg: str):
        if cls.LEVEL > cls.DEVELOP:
            return None
        print('[%s] %s' % (current_time(), msg))

    @classmethod
    def warning(cls, msg: str):
        print('[%s] %s' % (current_time(), msg))

    @classmethod
    def error(cls, msg: str):
        print('[%s] ERROR - %s' % (current_time(), msg))
