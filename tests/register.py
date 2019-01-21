#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Register Station
    ~~~~~~~~~~~~~~~~

    Generate Account information for DIM Station
"""

import unittest

import dimp


def number_string(number: int):
    string = '%010d' % number
    return string[:3] + '-' + string[3:-4] + '-' + string[-4:]


class StationTestCase(unittest.TestCase):

    def test_register(self):
        print('\n---------------- %s' % self)

        seed = 'gsp-s001'
        code = 110

        for index in range(0, 10000):
            sk = dimp.PrivateKey.generate({'algorithm': 'RSA'})
            meta = dimp.Meta.generate(seed, sk)
            # self.assertTrue(meta.key.match(sk))

            id1 = meta.generate_identifier(dimp.NetworkID.Station)
            # self.assertTrue(meta.match_identifier(id1))

            if id1.number // 10000000 == code:
                print('---- Mission Accomplished! ----')
                print(index, number_string(id1.number), id1)
                print('meta: ', meta)
                print('private key: ', sk)
                break

            if index % 10 == 0:
                print(index, number_string(id1.number), id1)


if __name__ == '__main__':
    unittest.main()
