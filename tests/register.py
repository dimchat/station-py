#! /usr/bin/env python3
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
    Register Accounts
    ~~~~~~~~~~~~~~~~~

    Generate Account information for DIM User/Station
"""

import unittest

import sys
import os

from dimp import Base64
from dimp import PrivateKey
from dimp import NetworkType, MetaType, Meta

from dimsdk import BTCAddress

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from station.config import g_facebook


class AccountTestCase(unittest.TestCase):

    def test_register(self):
        print('\n---------------- %s' % self)

        #
        #  prepare register parameters
        #
        cmd = 3
        if cmd == 1:
            # generate SP
            seed = 'gsp'
            network = NetworkType.PROVIDER
            print('*** registering SP (%s)' % seed)
        elif cmd == 2:
            # generate Station
            seed = 'gsp-s002'
            network = NetworkType.STATION
            print('*** registering station (%s)' % seed)
        elif cmd == 3:
            # generate robot
            seed = 'chatroom-admin'
            network = NetworkType.ROBOT
            print('*** registering robot (%s)' % seed)
        else:
            # generate User
            seed = 'moky'
            network = NetworkType.MAIN
            print('*** registering account (%s)' % seed)

        # seed
        data = seed.encode('utf-8')

        for index in range(0, 10000):

            # generate private key
            sk = PrivateKey.parse(key={'algorithm': 'RSA'})
            ct = sk.sign(data)
            # generate address
            address = BTCAddress.generate(fingerprint=ct, network=network)

            print('[% 5d] %s@%s' % (index, seed, address))

            meta = {
                'version': MetaType.DEFAULT,
                'seed': seed,
                'key': sk.public_key.dictionary,
                'fingerprint': Base64.encode(ct),
            }
            meta = Meta.parse(meta=meta)
            id1 = meta.generate_identifier(network=network)
            print('[% 5d] %s' % (index, id1))

            choice = ''
            while choice not in ['y', 'n']:
                choice = input('Save it (y/n)? ')

            if choice == 'y':
                print('---- Mission Accomplished! ----')
                print('**** ID:', id1)
                print('**** meta:\n', meta)
                print('**** private key:\n', sk)

                g_facebook.save_meta(identifier=id1, meta=meta)
                g_facebook.save_private_key(identifier=id1, key=sk)
                break


if __name__ == '__main__':
    unittest.main()
