# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from abc import abstractmethod
from typing import Optional


"""
    Star Ship
    ~~~~~~~~~

    Container carrying data package
"""


class Ship:
    """ Star Ship for carrying data package """

    @property
    def package(self) -> bytes:
        """ Get the package in this Ship """
        raise NotImplemented

    @property
    def sn(self) -> bytes:
        """ Get ID for this Ship """
        raise NotImplemented

    @property
    def payload(self) -> bytes:
        """ Get data containing in the package """
        raise NotImplemented


class ShipDelegate:
    """ Star Ship Delegate """

    @abstractmethod
    def ship_sent(self, ship: Ship, error: Optional[OSError] = None):
        """
        Callback when package sent

        :param ship:       package container
        :param error:      None on success
        """
        raise NotImplemented
