# -*- coding: utf-8 -*-

import json
from typing import Union, Optional

from udp.tlv.utils import base64_encode, base64_decode
from udp.tlv import Data, MutableData, VarIntData
from udp.mtp import Header, Package
from udp.mtp import TransactionID, DataType, Message as MessageDataType

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
    def create_message_package(cls, body, data_type: DataType=None, sn: TransactionID=None) -> Package:
        if data_type is None:
            data_type = MessageDataType
        if sn is None:
            sn = TransactionID.ZERO
        if not isinstance(body, Data):
            body = Data(data=body)
        return Package.new(data_type=data_type, sn=sn, body_length=body.length, body=body)

    @classmethod
    def message_from_data(cls, data: Data) -> Message:
        # noinspection PyArgumentList
        return Message.parse(data=data)

    @classmethod
    def __encode_data(cls, data: Union[bytes, Data]) -> Optional[str]:
        if data is None:
            return None
        elif isinstance(data, Data):
            data = data.get_bytes()
        return base64_encode(data=data)

    @classmethod
    def parse_keys(cls, data: Data) -> dict:
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
    def build_keys(cls, keys: dict) -> bytes:
        data = MutableData(capacity=512)
        for (identifier, base64) in keys.items():
            id_len = VarIntData(value=len(identifier))
            key_len = VarIntData(value=len(base64))
            if id_len.value > 0 and key_len.value > 0:
                data.append(id_len)
                data.append(StringValue(string=identifier))
                data.append(key_len)
                data.append(BinaryValue(data=base64_decode(string=base64)))
        return data.get_bytes()

    @classmethod
    def dmtp_to_reliable_message(cls, msg: Message) -> ReliableMessage:
        info = {
            'sender': msg.sender,
            'receiver': msg.receiver,
            'time': msg.time,
            'data': cls.__encode_data(data=msg.content),
            'signature': cls.__encode_data(data=msg.signature),
        }
        # symmetric key/keys
        key = msg.key
        if key is not None and key.length > 5:
            starts = key.slice(end=5).get_bytes()
            if starts == b'KEYS:':
                keys = cls.parse_keys(data=key.slice(start=5))
                info['keys'] = json.dumps(keys)
            else:
                info['key'] = cls.__encode_data(data=key)
        # attachments
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
        group = msg.group
        if group is not None:
            info['group'] = group
        msg_type = msg.type
        if msg_type > 0:
            info['type'] = msg_type
        # create reliable message
        return ReliableMessage(msg=info)

    @classmethod
    def dmtp_from_reliable_message(cls, msg: dict) -> Message:
        info = msg
        # convert content data
        content = info.get('data')
        if content is not None:
            info['data'] = base64_decode(string=content)
        # signature
        signature = info.get('signature')
        if signature is not None:
            info['signature'] = base64_decode(string=signature)
        # key/keys
        key = info.get('key')
        if key is None:
            keys = info.get('keys')
            if keys is not None:
                info['keys'] = cls.build_keys(keys=keys)
        else:
            info['key'] = base64_decode(string=key)
        # meta
        meta = info.get('meta')
        if meta is not None:
            # dict to JSON
            info['meta'] = json.dumps(meta).encode('utf-8')
        # profile
        profile = info.get('profile')
        if profile is not None:
            # dict to JSON
            info['profile'] = json.dumps(profile).encode('utf-8')
        return Message.new(info=info)

    @classmethod
    def dmtp_data_to_dimp_bytes(cls, data: Data) -> bytes:
        msg = cls.message_from_data(data=data)
        msg = cls.dmtp_to_reliable_message(msg=msg)
        return bytes(json.dumps(msg))

    @classmethod
    def dimp_bytes_to_dmtp_data(cls, data: bytes) -> Data:
        info: dict = json.loads(data)
        return cls.dmtp_from_reliable_message(msg=info)
