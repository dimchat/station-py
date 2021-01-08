# -*- coding: utf-8 -*-
#
#   DMTP: Direct Message Transfer Protocol
#
#                                Written in 2020 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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

import threading
import time
from typing import Optional

from dmtp.mtp.tlv import Data
from dmtp import Field
from dmtp import LocationValue, TimestampValue, BinaryValue
from dmtp import SourceAddressValue, MappedAddressValue, RelayedAddressValue
from dmtp import Peer


class Contact:

    EXPIRES = 3600 * 24  # 24 hours

    def __init__(self, identifier: str):
        super().__init__()
        self.__id = identifier
        self.__locations = []  # ordered by time
        self.__locations_lock = threading.Lock()

    @property
    def identifier(self) -> str:
        return self.__id

    @property
    def locations(self) -> list:
        """ Get all locations ordered by time (reversed) """
        reversed_locations = []
        with self.__locations_lock:
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                reversed_locations.append(self.__locations[pos])
        return reversed_locations

    def get_location(self, address: tuple) -> Optional[LocationValue]:
        """ Get location by (IP, port) """
        with self.__locations_lock:
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                item = self.__locations[pos]
                assert isinstance(item, LocationValue), 'location error: %s' % item
                if item.source_address == address:
                    return item
                if item.mapped_address == address:
                    return item

    def store_location(self, location: LocationValue) -> bool:
        """
        When received 'HI' command, update the location in it

        :param location: location info with time
        :return: False on error
        """
        if not self.verify_location(location=location):
            return False
        with self.__locations_lock:
            # check same location with different time
            source_address = location.source_address
            mapped_address = location.mapped_address
            timestamp = location.timestamp
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                item = self.__locations[pos]
                assert isinstance(item, LocationValue), 'location error: %s' % item
                if item.source_address != source_address:
                    continue
                if item.mapped_address != mapped_address:
                    continue
                if item.timestamp > timestamp:
                    # this location info is expired
                    return False
                # remove location(s) with same addresses
                self.__locations.pop(pos)
            # insert (ordered by time)
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                item = self.__locations[pos]
                assert isinstance(item, LocationValue), 'location error: %s' % item
                if item.timestamp <= location.timestamp:
                    # insert after it
                    pos += 1
                    break
            self.__locations.insert(pos, location)
            return True

    def clear_location(self, location: LocationValue) -> bool:
        """
        When receive 'BYE' command, remove the location in it

        :param location: location info with signature and time
        """
        if not self.verify_location(location=location):
            return False
        count = 0
        with self.__locations_lock:
            source_address = location.source_address
            mapped_address = location.mapped_address
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                item = self.__locations[pos]
                assert isinstance(item, LocationValue), 'location error: %s' % item
                if item.source_address != source_address:
                    continue
                if item.mapped_address != mapped_address:
                    continue
                # remove location(s) with same addresses
                self.__locations.pop(pos)
                count += 1
        return count > 0

    #
    #   Signature
    #

    @classmethod
    def __get_sign_data(cls, location: LocationValue) -> Optional[Data]:
        mapped_address = location.get(Field.MAPPED_ADDRESS)
        if mapped_address is None:
            return None
        source_address = location.get(Field.SOURCE_ADDRESS)
        relayed_address = location.get(Field.RELAYED_ADDRESS)
        timestamp = location.get(Field.TIME)
        # data = "source_address" + "mapped_address" + "relayed_address" + "time"
        assert isinstance(mapped_address, MappedAddressValue), 'mapped-address error: %s' % mapped_address
        data = mapped_address
        if source_address is not None:
            assert isinstance(source_address, SourceAddressValue), 'source-address error: %s' % source_address
            data = source_address.concat(data)
        if relayed_address is not None:
            assert isinstance(relayed_address, RelayedAddressValue), 'relayed-address error: %s' % relayed_address
            data = data.concat(relayed_address)
        if timestamp is not None:
            assert isinstance(timestamp, TimestampValue), 'timestamp value error: %s' % timestamp
            data = data.concat(timestamp)
        return data

    def sign_location(self, location: LocationValue) -> Optional[LocationValue]:
        data = self.__get_sign_data(location=location)
        if data is None:
            return None
        # TODO: sign it with private key
        sign = b'sign(' + data.get_bytes() + b')'
        signature = BinaryValue(data=sign)
        # create
        return LocationValue.new(identifier=location.identifier,
                                 source_address=location.source_address,
                                 mapped_address=location.mapped_address,
                                 relayed_address=location.relayed_address,
                                 timestamp=location.timestamp,
                                 signature=signature,
                                 nat=location.nat)

    def verify_location(self, location: LocationValue) -> bool:
        identifier = location.identifier
        if identifier is None:
            return False
        data = self.__get_sign_data(location=location)
        signature = location.signature
        if data is None or signature is None:
            return False
        # TODO: verify data and signature with public key
        return True

    def purge(self, peer: Peer):
        with self.__locations_lock:
            pos = len(self.__locations)
            while pos > 0:
                pos -= 1
                item = self.__locations[pos]
                assert isinstance(item, LocationValue), 'location error: %s' % item
                if self.is_expired(location=item, peer=peer):
                    self.__locations.pop(pos)

    @classmethod
    def is_expired(cls, location: LocationValue, peer: Peer=None) -> bool:
        """
        Check connection for client node; check timestamp for server node

        :param location: user's location info
        :param peer:     node peer
        :return: true to remove location
        """
        if peer is None:
            # check timestamp
            timestamp = location.timestamp
            if timestamp <= 0:
                return True
            return time.time() > (timestamp + cls.EXPIRES)
        # check connections
        error1 = False
        error2 = False
        now = time.time()
        # check source-address
        source_address = location.source_address
        if source_address is None:
            error1 = True
        else:
            conn = peer.get_connection(remote_address=source_address)
            if conn is not None and conn.is_error(now=now):
                error1 = True
        # check mapped-address
        mapped_address = location.mapped_address
        if mapped_address is None:
            error2 = True
        else:
            conn = peer.get_connection(remote_address=mapped_address)
            if conn is not None:
                return conn.is_error(now=now)
        return error1 and error2
