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
import re
import unittest

import sys
import os

from dimp import PrivateKey
from dimp import NetworkID, Meta

from mkm.address import DefaultAddress as BTCAddress
from mkm.types import MetaVersion

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.common import base64_encode
from station.config import g_facebook


def number_string(number: int):
    string = '%010d' % number
    return string[:3] + '-' + string[3:-4] + '-' + string[-4:]


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
            pattern = re.compile(r'^400\d+$')
            network = NetworkID.Provider
            print('*** registering SP (%s) with number match: %s' % (seed, pattern))
        elif cmd == 2:
            # generate Station
            seed = 'gsp-s002'
            pattern = re.compile(r'^110\d+$')
            network = NetworkID.Station
            print('*** registering station (%s) with number match: %s' % (seed, pattern))
        elif cmd == 3:
            # generate robot
            seed = 'chatroom-admin'
            pattern = re.compile(r'^000\d+$')
            network = NetworkID.Robot
            print('*** registering robot (%s) with number match: %s' % (seed, pattern))
        else:
            # generate User
            seed = 'moky'
            pattern = re.compile(r'^\d+9527$')
            network = NetworkID.Main
            print('*** registering account (%s) with number match: %s' % (seed, pattern))

        # seed
        data = seed.encode('utf-8')

        for index in range(0, 10000):

            # generate private key
            sk = PrivateKey({'algorithm': 'RSA'})
            ct = sk.sign(data)
            # generate address
            address = BTCAddress.new(data=ct, network=network)
            number = address.number

            if index % 10 == 0:
                print('[% 5d] %s : %s@%s' % (index, number_string(number), seed, address))

            if not pattern.match('%010d' % number):
                continue

            print('**** GOT IT!')
            meta = {
                'version': MetaVersion.Default,
                'seed': seed,
                'key': sk.public_key,
                'fingerprint': base64_encode(ct),
            }
            meta = Meta(meta)
            id1 = meta.generate_identifier(network=network)
            print('[% 5d] %s : %s' % (index, number_string(number), id1))

            choice = ''
            while choice not in ['y', 'n']:
                choice = input('Save it (y/n)? ')

            if choice == 'y':
                print('---- Mission Accomplished! ----')
                print('**** ID:', id1, 'number:', number_string(id1.number))
                print('**** meta:\n', meta)
                print('**** private key:\n', sk)

                g_facebook.save_meta(identifier=id1, meta=meta)
                g_facebook.save_private_key(identifier=id1, key=sk)
                break


if __name__ == '__main__':
    unittest.main()
