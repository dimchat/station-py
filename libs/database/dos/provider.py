# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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

from typing import Optional, List, Set, Tuple

from dimsdk import ID, Station

from dimples.common import ProviderDBI
from dimples.database.dos.base import template_replace
from dimples.database.dos import Storage


class ProviderStorage(Storage, ProviderDBI):
    """
        Provider Storage
        ~~~~~~~~~~~~~~~~
        file path: '.dim/private/neighbors.js'
    """
    neighbors_path = '{PRIVATE}/neighbors.js'

    def show_info(self):
        path = template_replace(self.neighbors_path, 'PRIVATE', self._private)
        print('!!! neighbors path: %s' % path)

    def __neighbors_path(self) -> str:
        path = self.neighbors_path
        return template_replace(path, 'PRIVATE', self._private)

    def save_neighbors(self, stations: Set[Tuple[str, int, ID]]) -> bool:
        """ save neighbor stations into file """
        path = self.__neighbors_path()
        self.info(msg='Saving neighbors into: %s' % path)
        array = revert_neighbors(stations=stations)
        return self.write_json(container=array, path=path)

    #
    #   Provider DBI
    #

    # Override
    def all_neighbors(self) -> Set[Tuple[str, int, Optional[ID]]]:
        """ load neighbors from file """
        path = self.__neighbors_path()
        self.info(msg='Loading neighbors from: %s' % path)
        array = self.read_json(path=path)
        if array is None:
            # neighbor stations not found
            return set()
        return convert_neighbors(stations=array)

    # Override
    def get_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        for station in neighbors:
            if host == station[0] and port == station[1]:
                return station[2]

    # Override
    def add_neighbor(self, host: str, port: int, identifier: ID = None) -> bool:
        neighbors = self.all_neighbors()
        if insert_neighbor(host=host, port=port, identifier=identifier, stations=neighbors):
            return self.save_neighbors(stations=neighbors)

    # Override
    def del_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        ok, sid = remove_neighbor(host=host, port=port, stations=neighbors)
        if ok:
            self.save_neighbors(stations=neighbors)
        return sid


def insert_neighbor(host: str, port: int, identifier: ID, stations: Set[Tuple[str, int, ID]]) -> bool:
    for item in stations:
        if item[0] == host and item[1] == port:
            # station already exists
            if item[2] == identifier or identifier is None:
                # ID not change
                return False
            # remove old record
            stations.discard(item)
            break
    # add new record
    station = (host, port, identifier)
    stations.add(station)
    return True


def remove_neighbor(host: str, port: int, stations: Set[Tuple[str, int, ID]]) -> (bool, ID):
    for item in stations:
        if item[0] == host and item[1] == port:
            # got it
            identifier = item[2]
            stations.discard(item)
            return True, identifier
    # neighbor station not found
    return False, None


def convert_neighbors(stations: List[list]) -> Set[Tuple[str, int, ID]]:
    """ convert stations from list to set """
    neighbors = set()
    for item in stations:
        host = item[0]
        port = int(item[1])
        sid = ID.parse(identifier=item[2])
        station = (host, port, sid)
        neighbors.add(station)
    return neighbors


def revert_neighbors(stations: Set[Tuple[str, int, ID]]) -> List[list]:
    """ revert stations from set to list """
    array = []
    for item in stations:
        if isinstance(item, Station):
            host = item.host
            port = item.port
            sid = item.identifier
        elif isinstance(item, dict):
            host = item['host']
            port = item.get('port', 9394)
            sid = item.get('ID')
        else:
            host = item[0]
            port = item[1]
            sid = item[2]
        if isinstance(sid, ID):
            sid = str(sid)
        # append: [str, int, str]
        array.append([host, port, sid])
    return array
