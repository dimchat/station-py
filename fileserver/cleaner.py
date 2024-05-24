# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    File Cleaner
    ~~~~~~~~~~~~

    Cleaning expired upload files
"""

import os
import traceback
from typing import Optional

from dimples import DateTime

from libs.utils import Singleton
from libs.utils import Runner, Logging


@Singleton
class FileCleaner(Runner, Logging):

    # clear files uploaded 49 days ago
    EXPIRES = 3600 * 24 * 49

    def __init__(self):
        super().__init__(interval=600.0)
        self.__next_time = 0
        self.__root = None
        Runner.thread_run(runner=self)

    @property
    def root(self) -> Optional[str]:
        return self.__root

    @root.setter
    def root(self, path: str):
        self.__root = path

    # Override
    async def process(self) -> bool:
        now = DateTime.current_timestamp()
        if now < self.__next_time:
            # last cleaning not expired yet
            return False
        else:
            self.__next_time = now + 3600
        # get upload directory
        root = self.root
        if root is None or len(root) < 8:
            self.error(msg='upload directory error: %s' % root)
            return False
        # try to clean upload directory
        try:
            expired = now - self.EXPIRES
            self.__clean_upload(root=root, expired=expired)
        except Exception as error:
            self.error('failed to clean upload directory: %s, %s' % (root, error))
            traceback.print_exc()
            return False

    def __clean_upload(self, root: str, expired: float):
        # assert root.startswith('/data/'), 'upload directory error: %s' % root
        when = DateTime.parse(expired)
        self.info(msg='cleaning uploaded files before: %s, root: %s' % (when, root))
        count = self.__clean_directory(path=root, expired=expired)
        self.info(msg='%d expired file(s) removed from: %s' % (count, root))

    def __clean_directory(self, path: str, expired: float) -> int:
        total = 0
        array = os.listdir(path)
        self.info(msg='checking directory: %s -> %s' % (path, array))
        for item in array:
            sub = os.path.join(path, item)
            # self.info(msg='checking: %s' % sub)
            if os.path.isdir(sub):
                total += self.__clean_directory(path=sub, expired=expired)
            elif not os.path.isfile(sub):
                self.warning(msg='ignore directory item: %s, parent: %s' % (item, path))
            elif self.__clean_file(path=sub, expired=expired):
                total += 1
            else:
                self.debug(msg='skip file: %s, parent: %s' % (item, path))
        return total

    def __clean_file(self, path: str, expired: float) -> bool:
        modified = os.path.getmtime(path)
        when = DateTime.parse(modified)
        if modified > expired:
            self.info(msg='file not expired yet: [%s] %s' % (when, path))
            return False
        else:
            self.warning(msg='removing expired file: [%s] %s' % (when, path))
            os.remove(path)
            return True
