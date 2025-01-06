#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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
    File Server
    ~~~~~~~~~~~

    DIM network supporting service
"""

from dimples.utils import Log, Runner
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from fileserver.shared import GlobalVariable
from fileserver.shared import create_config
from fileserver.cleaner import FileCleaner
from fileserver.handler import app


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/ftp.ini'


async def async_main():
    # create global variable
    shared = GlobalVariable()
    config = await create_config(app_name='File Server', default_config=DEFAULT_CONFIG)
    await shared.prepare(config=config)
    #
    #  Start cleaner
    #
    cleaner = FileCleaner()
    cleaner.root = shared.upload_directory
    #
    #  Start server
    #
    host = shared.server_host
    port = shared.server_port
    # app.run(host=host, port=port, debug=True)
    app.run(host=host, port=port)


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
