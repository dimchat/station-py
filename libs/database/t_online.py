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

from dimsdk import ID

from dimples.database.t_online import OnlineTable as SuperTable

from .redis import LoginCache


class OnlineTable(SuperTable):
    """ Implementations of OnlineDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__(root=root, public=public, private=private)
        self.__redis = LoginCache()

    #
    #   Online DBI
    #

    # Override
    def add_socket_address(self, identifier: ID, address: tuple) -> bool:
        # 1. store into memory cache
        super().add_socket_address(identifier=identifier, address=address)
        # 2. store into Redis Server
        return self.__redis.add_socket_address(identifier=identifier, address=address)

    # Override
    def remove_socket_address(self, identifier: ID, address: tuple) -> bool:
        # 1. remove from memory cache
        super().remove_socket_address(identifier=identifier, address=address)
        # 2. remove from Redis Server
        return self.__redis.remove_socket_address(identifier=identifier, address=address)
