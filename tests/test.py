#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Station Test
    ~~~~~~~~~~~~~~~~

    Unit test for DIM Station
"""

import unittest

import dimp


class StationTestCase(unittest.TestCase):

    def test_identifier(self):
        print('\n---------------- %s' % self)

        id1 = dimp.ID('gsp-s001@x77uVYBT1G48CLzW9iwe2dr5jhUNEM772G')
        self.assertEqual(id1.address.network, dimp.NetworkID.Station)


if __name__ == '__main__':
    unittest.main()
