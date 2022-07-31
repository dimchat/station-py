#! /usr/bin/env python3
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

"""
    Register Accounts
    ~~~~~~~~~~~~~~~~~

    Generate Account information for DIM User/Station
"""

import random

import sys
import os

from dimsdk import PrivateKey, EncryptKey
from dimsdk import NetworkType, ID, MetaType, Meta, Document, Visa

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from robots.config import g_facebook


def network_is_group(network: int) -> bool:
    return (network & NetworkType.GROUP) == NetworkType.GROUP


def get_opt(args: list, key: str):
    pos = len(args) - 1
    while pos >= 0:
        item: str = args[pos]
        if item == key:
            return args[pos + 1]
        if item.startswith('%s=' % key):
            return item[len(key)+1:]
        pos -= 1


def show_help(path):
    print('\n    Usages:'
          '\n        %s <command> [options]'
          '\n'
          '\n    Commands:'
          '\n        generate                Generate account.'
          '\n        modify                  Modify account info.'
          '\n        help                    Show help for commands.'
          '\n\n' % path)


def do_help(path: str, args):
    if len(args) == 1:
        cmd = args[0]
        if cmd == 'generate':
            print('\n'
                  '\n    Usages:'
                  '\n        %s generate <type> [options]'
                  '\n'
                  '\n    Description:'
                  '\n        Generate account with type, e.g. "USER", "GROUP", "STATION", "ROBOT".'
                  '\n'
                  '\n    Generate Options:'
                  '\n        --seed <username>       Generate meta with seed string.'
                  '\n        --founder <ID>          Generate group meta with founder ID.'
                  '\n\n' % path)
            return
        elif cmd == 'modify':
            print('\n'
                  '\n    Usages:'
                  '\n        %s modify <ID> [options]'
                  '\n'
                  '\n    Description:'
                  '\n        Modify account document with ID.'
                  '\n'
                  '\n    Modify Options:'
                  '\n        --name <name>           Change name for user/group.'
                  '\n        --avatar <URL>          Change avatar URL for user.'
                  '\n        --host <IP>             Change IP for station.'
                  '\n        --port <number>         Change port for station.'
                  '\n        --owner <ID>            Change group info with owner ID.'
                  '\n\n' % path)
            return
    print('\n'
          '\n    Usage:'
          '\n        %s help <command>'
          '\n'
          '\n    Description:'
          '\n        Show help for commands'
          '\n'
          '\n    Commands:'
          '\n        generate'
          '\n        modify'
          '\n\n' % path)


def do_generate(path: str, args):
    if args is not None and len(args) > 0:
        network_type = None
        meta_version = None
        seed = get_opt(args=args, key='--seed')
        # check account type
        a_type = args[0]
        if a_type in ['USER', 'User', 'user']:
            network_type = NetworkType.MAIN
            meta_version = MetaType.ETH
            if seed is None:
                seed = ''
        elif a_type in ['GROUP', 'Group', 'group']:
            network_type = NetworkType.GROUP
            meta_version = MetaType.DEFAULT
            if seed is None:
                seed = 'group-%d' % random.randint(10000, 100000000)
        elif a_type in ['STATION', 'Station', 'station']:
            network_type = NetworkType.STATION
            meta_version = MetaType.DEFAULT
            if seed is None:
                seed = 'station'
        elif a_type in ['ROBOT', 'Robot', 'robot']:
            network_type = NetworkType.ROBOT
            meta_version = MetaType.DEFAULT
            if seed is None:
                seed = 'robot'
        # check ID.type
        if network_type is not None:
            # 1. generate private key
            if network_is_group(network=network_type):
                # get private key from founder of group
                founder = ID.parse(get_opt(args=args, key='--founder'))
                if not isinstance(founder, ID):
                    return do_help(path=path, args=['generate'])
                pri_key = g_facebook.private_key_for_visa_signature(identifier=founder)
                assert isinstance(pri_key, PrivateKey), 'failed to get private key for founder: %s' % founder
            elif network_type in [NetworkType.STATION, NetworkType.ROBOT]:
                # generate private key for station/robot
                pri_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
                assert isinstance(pri_key, PrivateKey), 'failed to generate RSA key'
            else:
                # generate private key for user
                pri_key = PrivateKey.generate(algorithm=PrivateKey.ECC)
                assert isinstance(pri_key, PrivateKey), 'failed to generate ECC key'
            # 2. generate meta
            meta = Meta.generate(version=meta_version, key=pri_key, seed=seed)
            assert isinstance(meta, Meta), 'failed to generate meta'
            # 3. generate ID
            identifier = ID.generate(meta=meta, network=network_type)
            assert isinstance(identifier, ID), 'failed to generate ID'
            print('\n'
                  '\n    New ID: %s'
                  '\n\n' % identifier)
            # 4. save private key & meta
            if not network_is_group(network=network_type):
                g_facebook.save_private_key(key=pri_key, identifier=identifier)
            g_facebook.save_meta(meta=meta, identifier=identifier)
            return
    return do_help(path, ['generate'])


def do_modify(path: str, args):
    if len(args) > 0:
        identifier = ID.parse(identifier=args[0])
        assert isinstance(identifier, ID), 'ID error: %s' % args[0]
        name = get_opt(args=args, key='--name')
        if name is None:
            name = g_facebook.name(identifier=identifier)
        doc = g_facebook.document(identifier=identifier)
        if identifier.type == NetworkType.STATION:
            # modify station profile
            if doc is None:
                doc = Document.create(doc_type=Document.PROFILE, identifier=identifier)
            host = get_opt(args=args, key='--host')
            if host is not None:
                doc.set_property(key='host', value=host)
            else:
                host = doc.get_property(key='host')
            port = get_opt(args=args, key='--port')
            if port is not None:
                port = int(port)
                doc.set_property(key='port', value=port)
            else:
                port = doc.get_property(key='port')
                if port is None:
                    port = 0
            print('\n'
                  '\n    Modify Station: "%s"'
                  '\n'
                  '\n        name="%s"'
                  '\n        host="%s"'
                  '\n        port=%d'
                  '\n\n' % (identifier, name, host, port))
        elif identifier.is_user:
            # modify user visa
            if doc is None:
                doc = Document.create(doc_type=Document.VISA, identifier=identifier)
            assert isinstance(doc, Visa), 'user document error: %s -> %s' % (identifier, doc)
            avatar = get_opt(args=args, key='--avatar')
            if avatar is not None:
                doc.avatar = avatar
            else:
                avatar = doc.get_property(key='avatar')
            print('\n'
                  '\n    Modify User: "%s"'
                  '\n'
                  '\n        name="%s"'
                  '\n        avatar="%s"'
                  '\n\n' % (identifier, name, avatar))
        elif identifier.is_group:
            # modify group bulletin
            if doc is None:
                doc = Document.create(doc_type=Document.VISA, identifier=identifier)
            print('\n'
                  '\n    Modify Group: "%s"'
                  '\n'
                  '\n        name="%s"'
                  '\n\n' % (identifier, name))
        if doc is not None:
            doc.name = name
            if 'expires' in doc:
                del doc['expires']
            # sign document
            if network_is_group(network=identifier.type):
                # get private key from founder of group
                owner = ID.parse(get_opt(args=args, key='--owner'))
                if not isinstance(owner, ID):
                    return do_help(path=path, args=['modify'])
                sign_key = g_facebook.private_key_for_visa_signature(identifier=owner)
                assert isinstance(sign_key, PrivateKey), 'failed to get private key for owner: %s' % owner
            else:
                # check visa key for user
                dec_key = g_facebook.private_keys_for_decryption(identifier=identifier)
                if dec_key is None:
                    dec_key: PrivateKey = PrivateKey.generate(algorithm=PrivateKey.RSA)
                    ok = g_facebook.save_private_key(key=dec_key, identifier=identifier, key_type='V')
                    assert ok, 'failed to save private message key: %s' % identifier
                    enc_key = dec_key.public_key
                    assert isinstance(enc_key, EncryptKey), 'failed to get visa.key: %s' % identifier
                    assert isinstance(doc, Visa), 'user document error: %s' % doc
                    doc.key = enc_key
                # get private key from user
                sign_key = g_facebook.private_key_for_visa_signature(identifier=identifier)
                assert isinstance(sign_key, PrivateKey), 'failed to get private key: %s' % identifier
            doc.sign(private_key=sign_key)
            g_facebook.save_document(document=doc)
            return
    return do_help(path, ['modify'])


def parse_command(argv: list):
    path = argv[0]
    if len(argv) > 1:
        cmd = argv[1]
        # check command
        if cmd == 'generate':
            return do_generate(path=path, args=argv[2:])
        if cmd == 'modify':
            return do_modify(path=path, args=argv[2:])
        if cmd == 'help':
            return do_help(path=path, args=argv[2:])
    # command error
    return show_help(path=path)


if __name__ == '__main__':
    parse_command(argv=sys.argv)
