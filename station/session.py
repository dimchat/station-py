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
        self.session_key = hex_encode(bytes(numpy.random.bytes(32)))

    @classmethod
    def session(cls, identifier: dimp.ID):
        if identifier in sessions:
            return sessions[identifier]
        else:
            sess = Session(identifier=identifier)
            sessions[identifier] = sess
            return sess


sessions = {}
