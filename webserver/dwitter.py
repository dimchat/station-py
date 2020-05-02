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

import xmltodict
from flask import Response, request, render_template

from dimp import Address

from .config import BASE_URL
from .config import respond_xml, respond_js
from .config import g_facebook, app
from .worker import Worker

g_worker = Worker(facebook=g_facebook)


@app.route(BASE_URL+'/', methods=['GET'])
def home() -> Response:
    try:
        users = g_worker.outlines()
        xml = render_template('home.opml', users=users)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)


@app.route(BASE_URL+'/<string:address>', methods=['GET'])
@app.route(BASE_URL+'/<string:address>.rss', methods=['GET'])
@app.route(BASE_URL+'/<string:address>.json', methods=['GET'])
@app.route(BASE_URL+'/<string:address>.js', methods=['GET'])
def user(address: str) -> Response:
    path = request.path
    if path is None:
        ext = 'xml'
    elif path.endswith('.rss'):
        ext = 'rss'
    elif path.endswith('.js'):
        ext = 'js'
    elif path.endswith('.json'):
        ext = 'json'
    else:
        ext = 'xml'
    try:
        address = g_facebook.identifier(address)
        if len(address.name) == 0:
            address = address.address
        info = g_worker.user_info(identifier=address)
        if info is None:
            res = {'code': 404, 'name': 'Not Found', 'message': '%s not found' % address}
            xml = render_template('error.xml', result=res)
        else:
            identifier = g_facebook.identifier(info.get('ID'))
            messages = g_worker.messages(identifier)
            if ext == 'rss':
                xml = render_template('user.rss', user=info, messages=messages)
            else:
                xml = render_template('user.xml', user=info, messages=messages)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    if ext == 'js' or ext == 'json':
        info = xmltodict.parse(xml)
        if 'xml' in info:
            info = info['xml']
        elif 'result' in info:
            info = info['result']
        js = json.dumps(info)
        if ext == 'js':
            js = 'dwitter.js.respond(%s,{"path":"%s"});' % (js, path)
        return respond_js(js)
    else:
        return respond_xml(xml)


@app.route(BASE_URL+'/<int:year>/<int:mon>/<int:day>/<string:sig>', methods=['GET'])
@app.route(BASE_URL+'/<int:year>/<int:mon>/<int:day>/<string:sig>.xml', methods=['GET'])
def message(sig: str, year: int, mon: int, day: int) -> Response:
    try:
        msg = g_worker.message(signature=sig, year=year, month=mon, day=day)
        xml = render_template('msg.xml', msg=msg)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)


"""
    Meta
"""


@app.route(BASE_URL+'/<string:address>/meta.js', methods=['GET'])
def meta(address: str) -> Response:
    path = request.path
    try:
        address = g_facebook.identifier(address)
        m = g_facebook.meta(identifier=address)
        if m is None:
            res = {'code': 404, 'name': 'Not Found', 'message': '%s not found' % address}
        else:
            res = m
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
    js = json.dumps(res)
    js = 'dwitter.js.respond(%s,{"path":"%s"});' % (js, path)
    return respond_js(js)
