#! /usr/bin/env /usr/local/bin/python3
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
    Decentralized Witting Server
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import json

from flask import Response, request

from .config import BASE_URL
from .config import respond_js
from .config import g_facebook, app


"""
    Meta / Profile
"""


@app.route(BASE_URL+'meta/<string:address>.js', methods=['GET'])
@app.route(BASE_URL+'meta/<string:address>.json', methods=['GET'])
def meta(address: str) -> Response:
    path = request.path
    try:
        address = g_facebook.identifier(address)
        info = g_facebook.meta(identifier=address)
        if info is None:
            res = {'code': 404, 'name': 'Not Found', 'message': 'meta not found: %s' % address}
        else:
            res = info
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
    js = json.dumps(res)
    if path.endswith('.js'):
        # JS callback
        js = 'dim.js.respond(%s,{"path":"%s"});' % (js, path)
    return respond_js(js)


@app.route(BASE_URL+'profile/<string:address>.js', methods=['GET'])
@app.route(BASE_URL+'profile/<string:address>.json', methods=['GET'])
def profile(address: str) -> Response:
    path = request.path
    try:
        address = g_facebook.identifier(address)
        info = g_facebook.profile(identifier=address)
        if info is None:
            res = {'code': 404, 'name': 'Not Found', 'message': 'profile not found: %s' % address}
        else:
            res = info
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
    js = json.dumps(res)
    if path.endswith('.js'):
        # JS callback
        js = 'dim.js.respond(%s,{"path":"%s"});' % (js, path)
    return respond_js(js)
