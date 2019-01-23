#! /usr/bin/env python
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

import dimp


def number_string(number: int):
    string = '%010d' % number
    return string[:3] + '-' + string[3:-4] + '-' + string[-4:]


class AccountTestCase(unittest.TestCase):

    def test_register(self):
        print('\n---------------- %s' % self)

        seed = 'gsp-s001'
        network = dimp.NetworkID.Station

        number_prefix = 110

        for index in range(0, 10000):
            sk = dimp.PrivateKey.generate({'algorithm': 'RSA'})
            meta = dimp.Meta.generate(seed, sk)
            # self.assertTrue(meta.key.match(sk))

            id1 = meta.generate_identifier(network=network)
            # self.assertTrue(meta.match_identifier(id1))

            if id1.number // 10000000 == number_prefix:
                print('---- Mission Accomplished! ----')
                print('[% 3d] %s : %s' % (index, number_string(id1.number), id1))
                print('**** meta:\n', meta)
                print('**** private key:\n', sk)
                break

            if index % 10 == 0:
                print('[% 3d] %s : %s' % (index, number_string(id1.number), id1))


if __name__ == '__main__':
    unittest.main()
