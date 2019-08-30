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

from mkm import ID


class Storage:

    root = '/tmp/.dim'

    @classmethod
    def directory(cls, control: str, identifier: ID, sub_dir: str = '') -> str:
        path = os.path.join(cls.root, control, identifier.address)
        if len(sub_dir) > 0:
            path = os.path.join(path, sub_dir)
        return path

    @classmethod
    def exists(cls, path: str) -> bool:
        return os.path.exists(path)

    @classmethod
    def read_text(cls, path: str) -> str:
        if os.path.exists(path):
            # reading
            with open(path, 'r') as file:
                return file.read()

    @classmethod
    def read_json(cls, path: str) -> dict:
        text = cls.read_text(path)
        return json.loads(text)

    @classmethod
    def write_text(cls, text: str, path: str) -> bool:
        directory = os.path.dirname(path)
        # make sure the dirs exists
        if not os.path.exists(directory):
            os.makedirs(directory)
        # writing
        with open(path, 'w') as file:
            wrote = file.write(text)
            return wrote == len(text)

    @classmethod
    def write_json(cls, content: dict, path: str) -> bool:
        string = json.dumps(content)
        return cls.write_text(string, path)
