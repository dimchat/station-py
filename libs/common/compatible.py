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

from typing import Any, Dict

from mkm.factory import FactoryManager

from dimples import ReliableMessage
from dimples import DocumentCommand

from .protocol import ReceiptCommand


def get_meta_type(meta: Dict[str, Any]) -> int:
    """ get meta type(version) """
    version = meta.get('type')
    if version is None:
        version = meta.get('version')
        if version is not None:
            # fix it
            meta['type'] = version
    return 0 if version is None else int(version)


def patch():
    FactoryManager.general_factory.get_meta_type = get_meta_type


#
#  Compatible with old versions
#


# TODO: remove after all server/client upgraded
def fix_meta_attachment(msg: ReliableMessage):
    meta = msg.get('meta')
    if meta is not None:
        fix_meta_version(meta=meta)


def fix_meta_version(meta: dict):
    version = meta.get('version')
    if version is None:
        meta['version'] = meta['type']
    elif 'type' not in meta:
        meta['type'] = version


def copy_receipt_values(content: ReceiptCommand, env: dict):
    for key in ['sender', 'receiver', 'sn', 'signature']:
        value = env.get(key)
        if value is not None:
            content[key] = value


# TODO: remove after all server/client upgraded
def fix_receipt_command(content: ReceiptCommand):
    origin = content.get('origin')
    if origin is not None:
        # (v2.0)
        # compatible with v1.0
        content['envelope'] = origin
        # compatible with older version
        copy_receipt_values(content=content, env=origin)
        return content
    # check for old version
    env = content.get('envelope')
    if env is not None:
        # (v1.0)
        # compatible with v2.0
        content['origin'] = env
        # compatible with older version
        copy_receipt_values(content=content, env=env)
        return content
    # check for older version
    if 'sender' in content:  # and 'receiver' in content:
        # older version
        env = {
            'sender': content.get('sender'),
            'receiver': content.get('receiver'),
            'time': content.get('time'),
            'sn': content.get('sn'),
            'signature': content.get('signature'),
        }
        content['origin'] = env
        content['envelope'] = env
        return content


# TODO: remove after all server/client upgraded
def fix_document_command(content: DocumentCommand):
    info = content.get('document')
    if info is not None:
        # (v2.0)
        #    "ID"      : "{ID}",
        #    "document" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        return content
    info = content.get('profile')
    if info is None:
        # query document command
        return content
    # 1.* => 2.0
    content.pop('profile')
    if isinstance(info, str):
        # compatible with v1.0
        #    "ID"        : "{ID}",
        #    "profile"   : "{JsON}",
        #    "signature" : "{BASE64}"
        content['document'] = {
            'ID': str(content.identifier),
            'data': info,
            'signature': content.get("signature")
        }
    else:
        # compatible with v1.1
        #    "ID"      : "{ID}",
        #    "profile" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        content['document'] = info
    return content
