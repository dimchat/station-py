# -*- coding: utf-8 -*-

"""
    Info Loaders
    ~~~~~~~~~~~~

    Loading built-in accounts
"""

import os
from typing import Union

from dimp import ID, Meta, PrivateKey, Document, User
from dimsdk import Station

from libs.utils import Log
from libs.common import Storage, Server, CommonFacebook

etc = os.path.abspath(os.path.dirname(__file__))


"""
    Station Info Loaders
    ~~~~~~~~~~~~~~~~~~~~

    Loading station info from service provider configuration
"""


def load_station_info(identifier: ID, filename: str):
    return Storage.read_json(path=os.path.join(etc, str(identifier.address), filename))


def load_station(identifier: Union[ID, str], facebook: CommonFacebook) -> Station:
    """ Load station info from 'etc' directory

        :param identifier - station ID
        :param facebook - social network data source
        :return station with info from 'dims/etc/{address}/*'
    """
    identifier = ID.parse(identifier=identifier)
    # check meta
    meta = facebook.meta(identifier=identifier)
    if meta is None:
        # load from 'etc' directory
        meta = Meta.parse(meta=load_station_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for station: %s' % identifier)
        elif not facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey.parse(key=load_station_info(identifier=identifier, filename='secret.js'))
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
        profile = Document.create(doc_type=Document.PROFILE, identifier=identifier)
        profile.set_property('name', name)
        profile.set_property('host', host)
        profile.set_property('port', port)
        profile.sign(private_key=private_key)
        if not facebook.save_document(document=profile):
            raise AssertionError('failed to save profile: %s' % profile)
        # local station
        station = Server(identifier=identifier, host=host, port=port)
    facebook.cache_user(user=station)
    Log.info('station loaded: %s' % station)
    return station


#
#  Info Loader
#

def load_robot_info(identifier: ID, filename: str) -> dict:
    return Storage.read_json(path=os.path.join(etc, str(identifier.address), filename))


def load_user(identifier: str, facebook: CommonFacebook) -> User:
    identifier = ID.parse(identifier=identifier)
    # check meta
    try:
        meta = facebook.meta(identifier=identifier)
    except AssertionError:
        meta = None
    if meta is None:
        # load from 'etc' directory
        meta = Meta.parse(meta=load_robot_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for robot: %s' % identifier)
        elif not facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey.parse(key=load_robot_info(identifier=identifier, filename='secret.js'))
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
    profile = Document.create(doc_type=Document.VISA, identifier=identifier)
    profile.set_property('name', name)
    profile.set_property('avatar', avatar)
    profile.sign(private_key=private_key)
    if not facebook.save_document(document=profile):
        raise AssertionError('failed to save profile: %s' % profile)
    # create local user
    return facebook.user(identifier=identifier)
