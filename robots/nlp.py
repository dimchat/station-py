# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Chat Bots
    ~~~~~~~~~

    Chat bots from 3rd-party
"""

from typing import Optional, List

from libs.utils.nlp import ChatBot, Tuling, XiaoI

from etc.config import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores


def chat_bot(name: str) -> Optional[ChatBot]:
    if 'tuling' == name:
        if tuling_keys is None or tuling_ignores is None:
            return None
        # Tuling
        api_key = tuling_keys.get('api_key')
        assert api_key is not None, 'Tuling keys error: %s' % tuling_keys
        tuling = Tuling(api_key=api_key)
        # ignore codes
        for item in tuling_ignores:
            if item not in tuling.ignores:
                tuling.ignores.append(item)
        return tuling
    elif 'xiaoi' == name:
        if xiaoi_keys is None or xiaoi_ignores is None:
            return None
        # XiaoI
        app_key = xiaoi_keys.get('app_key')
        app_secret = xiaoi_keys.get('app_secret')
        assert app_key is not None and app_secret is not None, 'XiaoI keys error: %s' % xiaoi_keys
        xiaoi = XiaoI(app_key=app_key, app_secret=app_secret)
        # ignore responses
        for item in xiaoi_ignores:
            if item not in xiaoi.ignores:
                xiaoi.ignores.append(item)
        return xiaoi
    else:
        raise NotImplementedError('unknown chat bot: %s' % name)


def chat_bots(names: List[str]) -> List[ChatBot]:
    bots = []
    for n in names:
        b = chat_bot(name=n)
        if b is not None:
            bots.append(b)
    return bots
