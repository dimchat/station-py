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
    Web Server Config
    ~~~~~~~~~~~~~~~~~

    Configuration for WWW
"""

from dimsdk import AddressNameService
from dimsdk import KeyStore

#
#  Common Libs
#
from libs.common import Log
from libs.common import Database, Facebook, Messenger

from libs.common.immortals import moki_id, moki_sk, moki_meta, moki_profile
from libs.common.immortals import hulk_id, hulk_sk, hulk_meta, hulk_profile

#
#  Configurations
#
from etc.cfg_db import base_dir

"""
    Key Store
    ~~~~~~~~~

    Memory cache for reused passwords (symmetric key)
"""
g_keystore = KeyStore()

"""
    Database
    ~~~~~~~~

    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
g_database = Database()
g_database.base_dir = base_dir
Log.info("database directory: %s" % g_database.base_dir)

"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = Facebook()
g_facebook.database = g_database

"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""
g_ans = AddressNameService()
g_ans.database = g_database

"""
    Messenger
    ~~~~~~~~~
"""
g_messenger = Messenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore


def load_immortals():
    # load immortals
    Log.info('immortal user: %s' % moki_id)
    g_facebook.save_meta(identifier=moki_id, meta=moki_meta)
    g_facebook.save_private_key(identifier=moki_id, private_key=moki_sk)
    g_facebook.save_profile(profile=moki_profile)

    Log.info('immortal user: %s' % hulk_id)
    g_facebook.save_meta(identifier=hulk_id, meta=hulk_meta)
    g_facebook.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    g_facebook.save_profile(profile=hulk_profile)


"""
    Loading info
    ~~~~~~~~~~~~
"""

# load immortal accounts
Log.info('-------- loading immortals accounts')
load_immortals()

Log.info('======== configuration OK!')
