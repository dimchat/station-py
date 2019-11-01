#! /usr/bin/env python3
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

from dimp import MetaCommand, ProfileCommand

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
WWW_PORT = 8384

BASE_URI = '/dimp/v1'

app = Flask(__name__)


@app.route(BASE_URI+'/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route(BASE_URI+'/meta/<string:identifier>', methods=['GET'])
def query_meta(identifier: str) -> str:
    # check ID
    identifier = g_worker.identifier(identifier)
    if identifier is None:
        response = {
            'code': 400,  # Bad Request
            'message': 'ID error',
        }
    else:
        # get meta
        meta = g_worker.meta(identifier=identifier)
        if meta is None:
            response = {
                'code': 404,
                'message': 'Meta not found',
            }
        else:
            # response OK
            cmd = MetaCommand.new(identifier=identifier, meta=meta)
            response = {
                'code': 200,
                'message': 'OK',
                'content': cmd,
            }
    return jsonify(response)


@app.route(BASE_URI+'/profile/<string:identifier>', methods=['GET'])
def query_profile(identifier: str) -> str:
    # check ID
    identifier = g_worker.identifier(identifier)
    if identifier is None:
        response = {
            'code': 400,  # Bad Request
            'message': 'ID error',
        }
    else:
        # get profile
        profile = g_worker.profile(identifier=identifier)
        if profile is None:
            response = {
                'code': 404,
                'message': 'Profile not found',
            }
        else:
            # get meta
            meta = g_worker.meta(identifier=identifier)
            # response OK
            cmd = ProfileCommand.new(identifier=identifier, meta=meta, profile=profile)
            response = {
                'code': 200,
                'message': 'OK',
                'content': cmd,
            }
    return jsonify(response)


@app.route(BASE_URI+'/verify', methods=['POST'])
def verify_message() -> str:
    # post data
    form = request.form.to_dict()
    sender = form.get('sender')
    data = form.get('data')
    signature = form.get('signature')
    # check ID
    identifier = g_worker.identifier(sender)
    if identifier is None:
        response = {
            'code': 400,  # Bad Request
            'message': 'ID error',
        }
    else:
        # get meta
        meta = g_worker.meta(identifier=identifier)
        if meta is None:
            response = {
                'code': 404,
                'message': 'Meta not found',
            }
        else:
            # check signature with data
            data = g_worker.decode_data(data)
            signature = g_worker.decode_signature(signature)
            if data is None or signature is None:
                response = {
                    'code': 412,  # Precondition Failed
                    'message': 'Data or signature error',
                }
            elif meta.key.verify(data=data, signature=signature):
                response = {
                    'code': 200,
                    'message': 'OK',
                }
            else:
                response = {
                    'code': 403,  # Forbidden
                    'message': 'Signature not match',
                }
    return jsonify(response)


if __name__ == '__main__':
    app.run(host=WWW_HOST, port=WWW_PORT, debug=True)
