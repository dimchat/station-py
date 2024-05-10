#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Station bot: 'Octopus'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for bridging neighbor stations
"""

from dimples.utils import Log
from dimples.utils import Path
from dimples.utils import Runner
from dimples.edge.octopus import Octopus
from dimples.edge.shared import GlobalVariable
from dimples.edge.shared import create_config

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from sbots.shared import create_database, create_facebook


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/edge.ini'


async def main():
    # create global variable
    shared = GlobalVariable()
    # Step 1: load config
    config = create_config(app_name='DIM Network Edge', default_config=DEFAULT_CONFIG)
    shared.config = config
    # Step 2: create database
    db = await create_database(config=config)
    shared.adb = db
    shared.mdb = db
    shared.sdb = db
    # Step 3: create facebook
    sid = config.station_id
    assert sid is not None, 'current station ID not set: %s' % config
    facebook = await create_facebook(database=db, current_user=sid)
    shared.facebook = facebook
    # create & start octopus
    host = config.station_host
    port = config.station_port
    octopus = Octopus(shared=shared, local_host=host, local_port=port)
    await octopus.start()
    while octopus.running:
        await Runner.sleep(seconds=1.0)


if __name__ == '__main__':
    Runner.sync_run(main=main())
