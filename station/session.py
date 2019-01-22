# -*- coding: utf-8 -*-

import numpy
from binascii import b2a_hex, a2b_hex

import dimp


def hex_encode(data: bytes) -> str:
    """ HEX Encode """
    return b2a_hex(data).decode('utf-8')


def hex_decode(string: str) -> bytes:
    """ HEX Decode """
    return a2b_hex(string)


class Session:

    def __init__(self, identifier: dimp.ID):
        super().__init__()
        self.identifier = identifier
        self.client_address = None
        self.session_key = hex_encode(bytes(numpy.random.bytes(32)))


class SessionServer:

    def __init__(self):
        super().__init__()
        self.sessions = {}

    def session(self, identifier: dimp.ID) -> Session:
        if identifier in self.sessions:
            return self.sessions[identifier]
        else:
            sess = Session(identifier=identifier)
            self.sessions[identifier] = sess
            return sess

    def valid(self, identifier: dimp.ID, client_address) -> bool:
        if identifier not in self.sessions:
            return False
        sess = self.sessions[identifier]
        return sess.client_address == client_address
