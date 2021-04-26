# -*- coding: utf-8 -*-

import json
from typing import Optional

from dmtp.mtp.tlv.utils import base64_encode, base64_decode
from dmtp.mtp.tlv import Data, MutableData, VarIntData
from dmtp.mtp import Header, Package
from dmtp.mtp import DataType, TransactionID

from dmtp import Message
from dmtp import StringValue, BinaryValue

from dimp import ReliableMessage


class MTPUtils:

    @classmethod
    def parse_head(cls, data: bytes) -> Header:
        return Header.parse(data=Data(data=data))

    @classmethod
    def parse_package(cls, data: bytes) -> Package:
        return Package.parse(data=Data(data=data))

    @classmethod
    def create_package(cls, body, data_type: DataType, sn: TransactionID = None) -> Package:
        if not isinstance(body, Data):
            body = Data(data=body)
        return Package.new(data_type=data_type, sn=sn, body_length=body.length, body=body)

    @classmethod
    def serialize_message(cls, msg: ReliableMessage) -> bytes:
        info = msg.dictionary
        #
        #  body
        #
        content = info.get('data')
        if content is not None:
            assert isinstance(content, str), 'reliable message content error: %s' % content
            if content.startswith('{'):
                # JsON
                info['data'] = content.encode('utf-8')
            else:
                # Base64
                info['data'] = base64_decode(string=content)
        signature = info.get('signature')
        if signature is not None:
            assert isinstance(signature, str), 'reliable message signature error: %s' % signature
            info['signature'] = base64_decode(string=signature)
        # symmetric key/keys
        key = info.get('key')
        if key is None:
            keys = info.get('keys')
            if keys is not None:
                assert isinstance(keys, dict), 'reliable message keys error: %s' % keys
                # DMTP store both 'keys' and 'key' in 'key'
                info['key'] = b'KEYS:' + cls.__build_keys(keys=keys)
        else:
            assert isinstance(key, str), 'reliable message key error: %s' % key
            info['key'] = base64_decode(string=key)
        #
        #  attachments
        #
        meta = info.get('meta')
        if meta is not None:
            # dict to JSON
            assert isinstance(meta, dict), 'meta error: %s' % meta
            info['meta'] = json.dumps(meta).encode('utf-8')
        profile = info.get('profile')
        if profile is not None:
            # dict to JSON
            assert isinstance(profile, dict), 'profile error: %s' % profile
            info['profile'] = json.dumps(profile).encode('utf-8')

        # create as message
        msg = Message.new(info=info)
        return msg.get_bytes()

    @classmethod
    def deserialize_message(cls, data: bytes) -> Optional[ReliableMessage]:
        msg = Message.parse(data=Data(data=data))
        if msg is None or msg.sender is None or msg.receiver is None:
            raise ValueError('failed to deserialize data: %s' % data)
        #
        #  envelope
        #
        info = {
            'sender': msg.sender,
            'receiver': msg.receiver,
            'time': msg.time,
        }
        msg_type = msg.type
        if msg_type > 0:
            info['type'] = msg_type
        group = msg.group
        if group is not None:
            info['group'] = group
        #
        #  body
        #
        content = msg.content
        if content is not None:
            content = content.get_bytes()
            if content.startswith(b'{'):
                # JsON
                info['data'] = content.decode('utf-8')
            else:
                # Base64
                info['data'] = base64_encode(data=content)
        signature = msg.signature
        if signature is not None:
            info['signature'] = base64_encode(data=signature.get_bytes())
        # symmetric key/keys
        key = msg.key
        if key is not None and key.length > 5:
            starts = key.slice(end=5).get_bytes()
            if starts == b'KEYS:':
                info['keys'] = cls.__parse_keys(data=key.slice(start=5))
            else:
                info['key'] = base64_encode(data=key.get_bytes())
        #
        #  attachments
        #
        meta = msg.meta
        if meta is not None and meta.length > 0:
            # JSON to dict
            meta = meta.get_bytes().decode('utf-8')
            info['meta'] = json.loads(meta)
        profile = msg.profile
        if profile is not None and profile.length > 0:
            # JSON to dict
            profile = profile.get_bytes().decode('utf-8')
            info['profile'] = json.loads(profile)

        # create reliable message
        return ReliableMessage.parse(msg=info)

    @classmethod
    def __parse_keys(cls, data: Data) -> dict:
        keys = {}
        while data.length > 0:
            # get key length
            size = VarIntData(data=data)
            data = data.slice(start=size.length)
            # get key name
            name = StringValue(data=data.slice(end=size.value))
            data = data.slice(start=size.value)
            # get value length
            size = VarIntData(data=data)
            data = data.slice(start=size.length)
            # get value
            value = BinaryValue(data=data.slice(end=size.value))
            data = data.slice(start=size.value)
            assert name.length > 0, 'key name empty'
            if value.length > 0:
                keys[name.string] = base64_encode(data=value.get_bytes())
        return keys

    @classmethod
    def __build_keys(cls, keys: dict) -> bytes:
        data = MutableData(capacity=512)
        for (identifier, base64) in keys.items():
            id_value = StringValue(string=identifier)
            if id_value.length > 0 and base64 is not None and len(base64) > 0:
                key_value = BinaryValue(data=base64_decode(string=base64))
                data.append(VarIntData(value=id_value.length))
                data.append(id_value)
                data.append(VarIntData(value=key_value.length))
                data.append(key_value)
        return data.get_bytes()
