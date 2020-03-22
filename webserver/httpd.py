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
    Web Server
    ~~~~~~~~~~

    1. Query meta, profile
    2. Verify message
"""

import sys
import os

from flask import Flask, jsonify, render_template, request

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from webserver.worker import Worker


g_worker = Worker()


"""
    WWW Config
"""
WWW_HOST = '0.0.0.0'
WWW_PORT = 9395

BASE_URI = '/dimp/v1'

app = Flask(__name__)


@app.route(BASE_URI+'/dterm.html', methods=['GET'])
def dterm() -> str:
    return render_template('dterm.html')


@app.route(BASE_URI+'/dicq.html', methods=['GET'])
def dicq() -> str:
    return render_template('dicq.html')


@app.route(BASE_URI+'/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route(BASE_URI+'/<string:identifier>/meta.js', methods=['GET'])
def meta_file(identifier: str) -> str:
    response = g_worker.meta(identifier)
    if response is None:
        response = {
            'code': 404,
            'message': 'Meta not found',
        }
    return jsonify(response)


@app.route(BASE_URI+'/<string:identifier>/profile.js', methods=['GET'])
def profile_file(identifier: str) -> str:
    response = g_worker.profile(identifier)
    if response is None:
        response = {
            'code': 404,
            'message': 'Profile not found',
        }
    return jsonify(response)


@app.route(BASE_URI+'/meta/<string:identifier>', methods=['GET'])
def query_meta(identifier: str) -> str:
    # query meta with ID
    code, cmd = g_worker.query_meta(identifier)
    if code == 200:
        message = 'OK'
    elif code == 400:  # Bad Request
        message = 'ID error'
    elif code == 404:
        message = 'Meta not found'
    else:  # 500
        message = 'Internal Server Error'
    return jsonify({
        'code': code,
        'message': message,
        'content': cmd,
    })


@app.route(BASE_URI+'/profile/<string:identifier>', methods=['GET'])
def query_profile(identifier: str) -> str:
    # query profile with ID
    code, cmd = g_worker.query_profile(identifier)
    if code == 200:
        message = 'OK'
    elif code == 400:  # Bad Request
        message = 'ID error'
    elif code == 404:
        message = 'Profile not found'
    else:  # 500
        message = 'Internal Server Error'
    return jsonify({
        'code': code,
        'message': message,
        'content': cmd,
    })


@app.route(BASE_URI+'/verify', methods=['POST'])
def verify_message() -> str:
    # post data
    form = request.form.to_dict()
    sender = form.get('sender')
    data = form.get('data')
    signature = form.get('signature')
    # query meta with ID
    code, cmd = g_worker.query_meta(sender)
    # check signature and data with sender ID
    code = g_worker.verify_message(sender=sender, data=data, signature=signature)
    if code == 200:
        message = 'OK'
    elif code == 400:  # Bad Request
        message = 'ID error'
    elif code == 403:  # Forbidden
        message = 'Signature not match'
    elif code == 404:
        message = 'Meta not found'
    elif code == 412:  # Precondition Failed
        message = 'Data or signature error'
    else:
        message = 'Internal Server Error'
    return jsonify({
        'code': code,
        'message': message,
        'content': cmd,
    })


if __name__ == '__main__':
    app.run(host=WWW_HOST, port=WWW_PORT, debug=True)
