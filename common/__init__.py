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
    Common
    ~~~~~~

    I'm too lazy to write codes for demo project, so I borrow some utils here
    from the dimp packages, but I don't suggest you to do it also, because
    I won't promise these private utils will not be changed. Hia hia~ :P
                                             -- Albert Moky @ Jan. 23, 2019
"""

from mkm.crypto.utils import base64_encode, base64_decode
from dimp import Transceiver

from .hex import hex_encode, hex_decode
from .log import Log

# Immortal Accounts data for test
from .immortals import moki_id, moki_name, moki_pk, moki_sk, moki_meta, moki_profile, moki
from .immortals import hulk_id, hulk_name, hulk_pk, hulk_sk, hulk_meta, hulk_profile, hulk
from .providers import s001_id, s001_name, s001_pk, s001_sk, s001_meta, s001_profile, s001, s001_host, s001_port

from .facebook import Facebook, Barrack, scan_ids, load_accounts
from .keystore import KeyStore
from .database import Database


facebook = Facebook()
keystore = KeyStore()

database = Database()

facebook.entityDataSource = database
facebook.userDataSource = database
facebook.groupDataSource = database

transceiver = Transceiver()
transceiver.delegate = facebook
transceiver.barrack = facebook
transceiver.key_cache = keystore

s001.delegate = database
s001.transceiver = transceiver


__all__ = [
    'base64_encode', 'base64_decode',
    'hex_encode', 'hex_decode',
    'Log',

    'moki_id', 'moki_name', 'moki_pk', 'moki_sk', 'moki_meta', 'moki_profile', 'moki',
    'hulk_id', 'hulk_name', 'hulk_pk', 'hulk_sk', 'hulk_meta', 'hulk_profile', 'hulk',
    's001_id', 's001_name', 's001_pk', 's001_sk', 's001_meta', 's001_profile', 's001', 's001_host', 's001_port',

    'Facebook', 'Barrack', 'scan_ids', 'load_accounts',
    'KeyStore',
    'Database',

    'facebook', 'keystore', 'database', 'transceiver',
]
