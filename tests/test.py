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

    def test_btc(self):
        total_money = 2100 * 10000
        package = 50
        print('total BTC: %d, first package: %d' % (total_money, package))
        spent = 0
        order = 0
        day = 0
        year = 0
        while (spent + package) <= total_money:
            spent += package
            order += 1
            if order % (6 * 24) == 0:
                day += 1
                if day % 365 == 0:
                    year += 1
                    print('year %d, day %d: package=%f, spent=%f' % (year, day, package, spent))
                    if year % 4 == 0:
                        package /= 2.0
        print('BTC OVER! year=%d, day=%d, pack=%f, spent=%f, left=%f' % (year, day, package, spent, (total_money - spent)))

    def test_dimt(self):
        total_money = 15 * 10000 * 10000
        package = 2 ** 20
        print('total money: %d, first package: %d' % (total_money, package))
        spent = 0
        day = 0
        year = 0
        while (spent + package) <= total_money and package >= 1:
            spent += package
            day += 1
            if day % 365 == 0:
                year += 1
                print('year %d, day %d: package=%f, spent=%f' % (year, day, package, spent))
                if year % 2 == 0:
                    package /= 2.0
        print('DIMT OVER! year=%d, day=%d, pack=%f, spent=%f, left=%f' % (year, day, package, spent, (total_money - spent)))


if __name__ == '__main__':
    unittest.main()
