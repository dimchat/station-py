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
    Utilities
    ~~~~~~~~~

    I'm too lazy to write codes for demo project, so I borrow some utils here
    from the dimp packages, but I don't suggest you to do it also, because
    I won't promise these private utils will not be changed. Hia hia~ :P
                                             -- Albert Moky @ Jan. 23, 2019
"""

from dkd.utils import base64_encode, base64_decode

from .hex import hex_encode, hex_decode

# Immortal Accounts data for test
from ..immortals import moki_id, moki_pk, moki_sk, moki_meta, moki
from ..immortals import hulk_id, hulk_pk, hulk_sk, hulk_meta, hulk


__all__ = [
    'base64_encode', 'base64_decode',
    'hex_encode', 'hex_decode',

    'moki_id', 'moki_pk', 'moki_sk', 'moki_meta', 'moki',
    'hulk_id', 'hulk_pk', 'hulk_sk', 'hulk_meta', 'hulk',
]
