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
    File Manager
    ~~~~~~~~~~~~

    File access
"""

import os
from werkzeug.utils import secure_filename

import dimp


class FileManager:

    def __init__(self, base_dir='/tmp/www'):
        super().__init__()
        self.base_dir = base_dir
        self.extensions = {'png', 'jpg', 'jpeg'}

    def directory(self, sender: str) -> str:
        if '@' in sender:
            identifier = dimp.ID(sender)
            address = identifier.address
        else:
            address = dimp.Address(sender)
        return os.path.join(self.base_dir, secure_filename(address))

    def path(self, filename: str, sender: str) -> str:
        (root, ext) = os.path.splitext(filename)
        if ext is None or ext.replace('.', '').lower() not in self.extensions:
            raise TypeError('not supported file type: %s' % ext)
        return os.path.join(self.directory(sender=sender), secure_filename(filename))

    #
    #   save file data
    #
    def save(self, data: bytes, filename: str, sender: str) -> bool:
        if data is None or len(data) == 0 or filename is None or len(filename) == 0:
            raise AssertionError('filename or data cannot be empty')
        # make sure the sub directories exist
        directory = self.directory(sender=sender)
        if not os.path.exists(directory):
            os.makedirs(directory)
        # write file
        path = self.path(filename=filename, sender=sender)
        with open(path, 'wb') as file:
            count = file.write(data)
        return count == len(data)

    #
    #   load file data
    #
    def load(self, filename: str, sender: str) -> bytes:
        path = self.path(filename=filename, sender=sender)
        if os.path.isfile(path):
            with open(path, 'rb') as file:
                data = file.read()
            return data
