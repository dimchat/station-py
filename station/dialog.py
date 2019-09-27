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
    Dialog Robot
    ~~~~~~~~~~~~

    Dialog for chatting with station
"""

import json
import urllib.request
from abc import ABCMeta, abstractmethod
from typing import Optional

import numpy
from dimp import ID
from dimp import Content, TextContent

from common import Log, hex_encode, sha1


class ChatBot(metaclass=ABCMeta):

    @abstractmethod
    def ask(self, question: str, user: str=None) -> str:
        """Talking with the chat bot

            :param question - message
            :param user - sender ID
            :return answer
        """
        pass


class Tuling(ChatBot):

    def __init__(self):
        super().__init__()
        self.user_id = 'dimchat'
        self.api_key = '8cbbdaf0baea412296800444895a75be'
        self.api_url = 'http://openapi.tuling123.com/openapi/api/v2'

    def __request(self, text: str) -> str:
        return json.dumps({
            'perception': {
                'inputText': {
                    'text': text,
                },
            },
            'selfInfo': {
                'location': {
                    'province': 'Guangdong',
                    'city': 'Guangzhou',
                }
            },
            'userInfo': {
                'apiKey': self.api_key,
                'userId': self.user_id,
            }
        })

    def __post(self, text: str) -> dict:
        request = self.__request(text=text)
        headers = {'content-type': 'application/json'}
        Log.info('request: %s\n%s\n%s' % (self.api_url, headers, request))
        http_post = urllib.request.Request(self.api_url, data=request.encode('utf-8'), headers=headers)
        response = urllib.request.urlopen(http_post)
        data: bytes = response.read()
        if data is not None and len(data) > 0:
            # assert data[0] == ord('{') and data[-1] == ord('}'), 'response error: %s' % data
            return json.loads(data)

    @staticmethod
    def __fetch(response: dict) -> Optional[str]:
        # get code
        intent: dict = response.get('intent')
        if intent is not None:
            code = intent.get('code')
            if code == 4003:
                # requests limited for test, ignore it
                return None
        # get text
        results: list = response.get('results')
        if results is not None and len(results) > 0:
            values: dict = results[0].get('values')
            if values is not None:
                return values.get('text')

    def ask(self, question: str, user: str=None) -> str:
        if user is not None:
            self.user_id = user
        response = self.__post(text=question)
        if response is not None:
            Log.info('response: %s' % response)
            return self.__fetch(response)


def sha_hex(string: str) -> str:
    return hex_encode(sha1(string.encode('utf-8')))


class XiaoI(ChatBot):

    def __init__(self):
        super().__init__()
        self.user_id = 'dimchat'
        self.key = 'open1_1BALCbHT4f2k'
        self.secret = 'mzMzWQ6kpUztmVvCDXyy'
        # self.api_url = 'http://nlp.xiaoi.com/ask.do'
        self.api_url = 'http://robot.open.xiaoi.com/ask.do'

    def __request(self, text: str) -> str:
        return 'question=' + text + '&userId=' + self.user_id + '&platform=weixin&type=0'

    def __auth(self) -> str:
        realm = 'xiaoi.com'
        method = 'POST'
        uri = '/ask.do'
        random: bytes = numpy.random.bytes(40)  # random data
        nonce = hex_encode(random)
        # sign
        ha1 = sha_hex(self.key + ':' + realm + ':' + self.secret)
        ha2 = sha_hex(method + ':' + uri)
        sign = sha_hex(ha1 + ':' + nonce + ':' + ha2)
        return 'app_key="' + self.key + '", nonce="' + nonce + '", signature="' + sign + '"'

    def __post(self, text: str) -> str:
        request = self.__request(text=text)
        headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Auth': self.__auth(),
        }
        Log.info('request: %s\n%s\n%s' % (self.api_url, headers, request))
        http_post = urllib.request.Request(self.api_url, data=request.encode('utf-8'), headers=headers)
        response = urllib.request.urlopen(http_post)
        data: bytes = response.read()
        if data is not None:
            return data.decode('utf-8')

    @staticmethod
    def __fetch(response: str) -> Optional[str]:
        if response == '默认回复':
            return None
        return response

    def ask(self, question: str, user: str = None) -> str:
        if user is not None:
            self.user_id = user
        response = self.__post(text=question)
        if response is not None:
            Log.info('response: %s' % response)
            return self.__fetch(response)


class Dialog:

    def __init__(self):
        super().__init__()
        # TODO: random robot list
        self.robots: list = [Tuling(), XiaoI()]

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def __ask(self, question: str, sender: ID) -> str:
        # try each chat robots
        for robot in self.robots:
            answer = robot.ask(question=question, user=sender.address)
            if answer is not None:
                return answer

    def talk(self, content: Content, sender: ID) -> Content:
        if isinstance(content, TextContent):
            question = content.text
            answer = self.__ask(question=question, sender=sender)
            if answer is not None:
                return TextContent.new(text=answer)
        # TEST: response client with the same message here
        return content
