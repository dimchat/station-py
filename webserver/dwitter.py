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

from dimp import ID, Address, Meta, Document

from .config import BASE_URL
from .config import respond_xml, respond_js
from .config import g_facebook, app
from .worker import Worker

g_worker = Worker(facebook=g_facebook)


@app.route(BASE_URL, methods=['GET'])
def home() -> Response:
    try:
        users = g_worker.outlines()
        xml = render_template('home.opml', users=users)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)


@app.route(BASE_URL+'profile', methods=['POST'])
def upload_profile() -> Response:
    try:
        form = request.form.to_dict()
        identifier = form['ID']
        meta = form['meta']
        profile = form['profile']
        identifier = ID.parse(identifier=identifier)
        # save meta
        if meta is None:
            meta = g_facebook.meta(identifier=identifier)
            if meta is None:
                raise LookupError('meta not found: %s' % identifier)
        else:
            meta = Meta.parse(meta=json.loads(meta))
            if not g_facebook.save_meta(meta=meta, identifier=identifier):
                raise ValueError('meta not acceptable: %s' % identifier)
        # save profile
        if profile is None:
            raise ValueError('profile empty: %s' % identifier)
        else:
            profile = Document.parse(document=json.loads(profile))
            if not g_facebook.save_document(document=profile):
                raise ValueError('profile not acceptable: %s' % identifier)
        # OK
        return user(identifier)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)


@app.route(BASE_URL+'user/<string:address>', methods=['GET'])
def user(address: str) -> Response:
    try:
        if address.find('@') < 0:
            address = Address.parse(address=address)
        identifier = ID.parse(identifier=address)
        info = g_worker.user_info(identifier=identifier)
        if info is None:
            messages = []
        else:
            identifier = ID.parse(identifier=info.get('ID'))
            messages = g_worker.messages(identifier=identifier, start=0, count=20)
        xml = render_template('user.xml', user=info, messages=messages)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)


@app.route(BASE_URL+'channel/<string:address>', methods=['GET'])
@app.route(BASE_URL+'channel/<string:address>.rss', methods=['GET'])
@app.route(BASE_URL+'channel/<string:address>.json', methods=['GET'])
@app.route(BASE_URL+'channel/<string:address>.js', methods=['GET'])
def channel(address: str) -> Response:
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
        if address.find('@') < 0:
            address = Address.parse(address=address)
        identifier = ID.parse(identifier=address)
        info = g_worker.user_info(identifier=identifier)
        if info is None:
            res = {'code': 404, 'name': 'Not Found', 'message': '%s not found' % address}
            xml = render_template('error.xml', result=res)
        else:
            start = request.args.get('start')
            count = request.args.get('count')
            if start is None:
                start = 0
            else:
                start = int(start)
            if count is None:
                count = 20
            else:
                count = int(count)
            identifier = ID.parse(identifier=info.get('ID'))
            messages = g_worker.messages(identifier=identifier, start=start, count=count)
            if ext == 'rss':
                xml = render_template('channel.rss', user=info, messages=messages)
            else:
                xml = render_template('channel.xml', user=info, messages=messages)
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


@app.route(BASE_URL+'message/<string:sig>', methods=['GET'])
@app.route(BASE_URL+'message/<string:sig>.xml', methods=['GET'])
def message(sig: str) -> Response:
    try:
        msg = g_worker.message(signature=sig)
        xml = render_template('message.xml', msg=msg)
    except Exception as error:
        res = {'code': 500, 'name': 'Internal Server Error', 'message': '%s' % error}
        xml = render_template('error.xml', result=res)
    return respond_xml(xml)
