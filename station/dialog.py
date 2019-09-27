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
from typing import Optional

from dimp import ID
from dimp import Content, TextContent

from common import Log

from .config import g_facebook


class Tuling123Com:

    def __init__(self):
        super().__init__()
        self.user_id = 513411
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
        }).encode('utf-8')

    def __post(self, text: str) -> dict:
        request = self.__request(text=text)
        headers = {'content-type': 'application/json'}
        http_post = urllib.request.Request(self.api_url, data=request, headers=headers)
        response = urllib.request.urlopen(http_post)
        data = response.read()
        if data is not None:
            return json.loads(data)

    @staticmethod
    def __fetch(response: dict) -> Optional[str]:
        # get code
        intent = response.get('intent')
        if intent is not None:
            code = intent.get('code')
            if code == 4003:
                # requests limited for test, ignore it
                return None
        # get text
        results = response.get('results')
        if results is not None and len(results) > 0:
            values = results[0].get('values')
            if values is not None:
                return values.get('text')

    def post(self, text: str) -> str:
        response = self.__post(text=text)
        if response is not None:
            Log.info('response: %s' % response)
            return self.__fetch(response)


class Dialog:

    def __init__(self):
        super().__init__()
        self.tuling = Tuling123Com()

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def __send(self, msg: str) -> str:
        # try tuling chat robot
        answer = self.tuling.post(text=msg)
        if answer is not None:
            return answer
        # TODO: if no answer, try other robot

    def talk(self, content: Content, sender: ID) -> Content:
        nickname = g_facebook.nickname(identifier=sender)
        if nickname is None:
            self.info('talking with %s' % sender)
        else:
            self.info('talking with %s' % nickname)
        if isinstance(content, TextContent):
            question = content.text
            answer = self.__send(msg=question)
            if answer is not None:
                return TextContent.new(text=answer)
        # TEST: response client with the same message here
        return content
