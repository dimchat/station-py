# -*- coding: utf-8 -*-
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

from typing import Optional, Set, Tuple

from dimsdk import utf8_encode, utf8_decode, json_encode, json_decode
from dimsdk import ID

from ..dos.provider import insert_neighbor, remove_neighbor
from ..dos.provider import convert_neighbors, revert_neighbors

from .base import Cache


class ProviderCache(Cache):

    # provider info cached in Redis will be removed after 10 hours, after that
    # it should be reloaded from local storage
    EXPIRES = 36000  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'dim'

    @property  # Override
    def tbl_name(self) -> str:
        return 'isp'

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dim.isp.neighbors'
    """
    def __neighbors_key(self) -> str:
        return '%s.%s.neighbors' % (self.db_name, self.tbl_name)

    def save_neighbors(self, stations: Set[Tuple[str, int, ID]]) -> bool:
        sp_key = self.__neighbors_key()
        array = revert_neighbors(stations=stations)
        js = json_encode(obj=array)
        value = utf8_encode(string=js)
        self.set(name=sp_key, value=value, expires=self.EXPIRES)
        return True

    def all_neighbors(self) -> Set[Tuple[str, int, Optional[ID]]]:
        sp_key = self.__neighbors_key()
        value = self.get(name=sp_key)
        if value is None:
            # neighbor stations not found
            return set()
        js = utf8_decode(data=value)
        array = json_decode(string=js)
        return convert_neighbors(stations=array)

    def get_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        for station in neighbors:
            if host == station[0] and port == station[1]:
                return station[2]

    def add_neighbor(self, host: str, port: int, identifier: ID = None) -> bool:
        neighbors = self.all_neighbors()
        if insert_neighbor(host=host, port=port, identifier=identifier, stations=neighbors):
            return self.save_neighbors(stations=neighbors)

    def del_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        ok, sid = remove_neighbor(host=host, port=port, stations=neighbors)
        if ok:
            self.save_neighbors(stations=neighbors)
        return sid
