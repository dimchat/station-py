# -*- coding: utf-8 -*-

"""
    Genesis Service Providers
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Configuration of stations
"""

from dimp import ID

"""
    Current Station
    ~~~~~~~~~~~~~~~
    
    Local Server
"""
station_id = ID('gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC')
station_name = 'Genesis Station (HK)'
station_host = '0.0.0.0'
station_port = 9394

"""
    Station List
    ~~~~~~~~~~~~

    All stations of current Service Provider
"""

stations = [
    ID('gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'),
    ID('gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW'),
]


def neighbor_stations(identifier: ID) -> list:
    """ Get neighbor stations for broadcast """
    assert identifier in stations, 'current station not exists: %s' % identifier
    count = len(stations)
    if count <= 1:
        # only 1 station, no neighbors
        return []
    # current station's position
    pos = stations.index(identifier)
    array = []
    # get left node
    left = stations[pos - 1]
    assert left != identifier, 'stations error: %s' % stations
    array.append(left)
    if count > 2:
        # get right node
        right = stations[(pos + 1) % count]
        assert right != identifier and right != left, 'stations error: %s' % stations
        array.append(right)
    return array
