#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Station Test
    ~~~~~~~~~~~~~~~~

    Unit test for DIM Station
"""

import unittest

from dimp import ID, NetworkID


class StationTestCase(unittest.TestCase):

    def test_identifier(self):
        print('\n---------------- %s' % self)

        id1 = ID('gsp-s001@x77uVYBT1G48CLzW9iwe2dr5jhUNEM772G')
        self.assertEqual(id1.address.network, NetworkID.Station)


if __name__ == '__main__':
    unittest.main()
