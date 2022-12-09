# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Chat Bot: XiaoI
    ~~~~~~~~~~~~~~~

    AI chat bot powered by XiaoI
"""

import urllib.request
from typing import Optional

from dimples import hex_encode, utf8_encode, utf8_decode, sha1
from dimples.utils import random_bytes

from .chatbot import ChatBot


def sha_hex(string: str) -> str:
    return hex_encode(data=sha1(data=utf8_encode(string=string)))


class XiaoI(ChatBot):

    def __init__(self, app_key: str, app_secret: str):
        super().__init__()
        self.user_id = 'dimchat'
        self.app_key = app_key
        self.app_secret = app_secret
        # self.api_url = 'http://nlp.xiaoi.com/ask.do'
        self.api_url = 'http://robot.open.xiaoi.com/ask.do'
        # parameters for auth
        self.realm = 'xiaoi.com'
        self.uri = '/ask.do'
        self.method = 'POST'
        # ignore responses
        self.ignores = ['默认回复', '重复回复']

    def __request(self, text: str) -> str:
        return 'type=0&platform=dim&userId=%s&question=%s' % (self.user_id, text)

    def __auth(self) -> str:
        random: bytes = random_bytes(40)
        nonce = hex_encode(random)
        # sign
        ha1 = sha_hex(self.app_key + ':' + self.realm + ':' + self.app_secret)
        ha2 = sha_hex(self.method + ':' + self.uri)
        sign = sha_hex(ha1 + ':' + nonce + ':' + ha2)
        return 'app_key="' + self.app_key + '", nonce="' + nonce + '", signature="' + sign + '"'

    def __post(self, text: str) -> str:
        request = self.__request(text=text)
        headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Auth': self.__auth(),
        }
        http_post = urllib.request.Request(self.api_url, data=utf8_encode(string=request), headers=headers)
        response = urllib.request.urlopen(http_post)
        data: bytes = response.read()
        if data is not None:
            return utf8_decode(data=data)

    def __fetch(self, response: str) -> Optional[str]:
        # check blah blah
        if response in self.ignores:
            # no answer, ignore it
            return None
        # got it
        return response

    def ask(self, question: str, user: str = None) -> str:
        if user is not None:
            self.user_id = user
        response = self.__post(text=question)
        if response is not None:
            return self.__fetch(response)
