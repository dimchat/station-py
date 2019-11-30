# -*- coding: utf-8 -*-

"""
    Info Loaders
    ~~~~~~~~~~~~

    Loading built-in accounts
"""

import os

from dimp import ID, Meta, PrivateKey, Profile, User
from dimsdk import Station, Facebook

from libs.common import Storage, Log, Server

etc = os.path.abspath(os.path.dirname(__file__))


"""
    Station Info Loaders
    ~~~~~~~~~~~~~~~~~~~~

    Loading station info from service provider configuration
"""


def load_station_info(identifier: ID, filename: str):
    return Storage.read_json(path=os.path.join(etc, identifier.address, filename))


def load_station(facebook: Facebook, identifier: str) -> Station:
    """ Load station info from 'etc' directory

        :param identifier - station ID
        :param facebook - social network data source
        :return station with info from 'dims/etc/{address}/*'
    """
    identifier = facebook.identifier(identifier)
    # check meta
    meta = facebook.meta(identifier=identifier)
    if meta is None:
        # load from 'etc' directory
        meta = Meta(load_station_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for station: %s' % identifier)
        elif not facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey(load_station_info(identifier=identifier, filename='secret.js'))
        if private_key is None:
            pass
        elif not facebook.save_private_key(key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
    # check profile
    profile = load_station_info(identifier=identifier, filename='profile.js')
    if profile is None:
        raise LookupError('failed to get profile for station: %s' % identifier)
    Log.info('station profile: %s' % profile)
    name = profile.get('name')
    host = profile.get('host')
    port = profile.get('port')
    # create station
    if private_key is None:
        # remote station
        station = Station(identifier=identifier, host=host, port=port)
    else:
        # create profile
        profile = Profile.new(identifier=identifier)
        profile.set_property('name', name)
        profile.set_property('host', host)
        profile.set_property('port', port)
        profile.sign(private_key=private_key)
        if not facebook.save_profile(profile=profile):
            raise AssertionError('failed to save profile: %s' % profile)
        # local station
        station = Server(identifier=identifier, host=host, port=port)
    facebook.cache_user(user=station)
    Log.info('station loaded: %s' % station)
    return station


def neighbor_stations(facebook: Facebook, identifier: str, all_stations: list) -> list:
    """ Get neighbor stations for broadcast """
    identifier = facebook.identifier(identifier)
    count = len(all_stations)
    if count <= 1:
        # only 1 station, no neighbors
        return []
    # current station's position
    pos = 0
    for station in all_stations:
        if station.identifier == identifier:
            # got it
            break
        pos = pos + 1
    assert pos < count, 'current station not found: %s, %s' % (identifier, all_stations)
    array = []
    # get left node
    left = all_stations[pos - 1]
    assert left.identifier != identifier, 'stations error: %s' % all_stations
    array.append(left)
    if count > 2:
        # get right node
        right = all_stations[(pos + 1) % count]
        assert right.identifier != identifier, 'stations error: %s' % all_stations
        assert right.identifier != left.identifier, 'stations error: %s' % all_stations
        array.append(right)
    return array


#
#  Info Loader
#

def load_robot_info(identifier: ID, filename: str) -> dict:
    return Storage.read_json(path=os.path.join(etc, identifier.address, filename))


"""
    Client
    ~~~~~~

"""


def load_user(facebook: Facebook, identifier: str) -> User:
    identifier = facebook.identifier(identifier)
    # check meta
    meta = facebook.meta(identifier=identifier)
    if meta is None:
        # load from 'etc' directory
        meta = Meta(load_robot_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for robot: %s' % identifier)
        elif not facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey(load_robot_info(identifier=identifier, filename='secret.js'))
        if private_key is None:
            pass
        elif not facebook.save_private_key(key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
    if private_key is None:
        raise AssertionError('private key not found for ID: %s' % identifier)
    # check profile
    profile = load_robot_info(identifier=identifier, filename='profile.js')
    if profile is None:
        raise LookupError('failed to get profile for robot: %s' % identifier)
    Log.info('robot profile: %s' % profile)
    name = profile.get('name')
    avatar = profile.get('avatar')
    # create profile
    profile = Profile.new(identifier=identifier)
    profile.set_property('name', name)
    profile.set_property('avatar', avatar)
    profile.sign(private_key=private_key)
    if not facebook.save_profile(profile):
        raise AssertionError('failed to save profile: %s' % profile)
    # create local user
    return facebook.user(identifier=identifier)
