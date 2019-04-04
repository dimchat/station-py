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
    File Server
    ~~~~~~~~~~~

    Upload/download image files
"""

import hashlib
from binascii import b2a_hex

from werkzeug.utils import secure_filename
from flask import Flask, request, send_from_directory, render_template

import dimp

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

HOST = '0.0.0.0'
PORT = 8081

# AVATAR_DIRECTORY = '/tmp/www/avatars'
AVATAR_DIRECTORY = '/data/.dim/avatars'

# UPLOAD_DIRECTORY = '/tmp/www/uploads'
UPLOAD_DIRECTORY = '/data/.dim/uploads'

ALLOWED_FILE_TYPES = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4'}
IMAGE_FILE_TYPES = {'png', 'jpg', 'jpeg'}


def md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


def hex_encode(data: bytes) -> str:
    return b2a_hex(data).decode('utf-8')


def save_data(data: bytes, filename: str, identifier: dimp.ID) -> str:
    """ save encrypted data file """
    (useless, ext) = os.path.splitext(filename)
    if ext is None or data is None:
        # 417 - Expectation Failed
        msg = 'Expectation Failed'
        return render_template('response.html', code=417, message=msg, filename=filename)
    ext = ext.replace('.', '').lower()
    if ext not in ALLOWED_FILE_TYPES:
        # 415 - Unsupported Media Type
        msg = 'File extensions not support: %s' % ext
        return render_template('response.html', code=415, message=msg, filename=filename)
    # save it with real filename
    filename = '%s.%s' % (hex_encode(md5(data)), ext)
    save_dir = os.path.join(UPLOAD_DIRECTORY, identifier.address)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    path = os.path.join(save_dir, filename)
    with open(path, 'wb') as file:
        count = file.write(data)
    # OK
    if count == len(data):
        # 200 - OK
        return render_template('response.html', code=200, message='OK', filename=filename)
    # 500 - Internal Server Error
    return render_template('response.html', code=500, message='Internal Server Error', filename=filename)


def save_avatar(data: bytes, filename: str, identifier: dimp.ID) -> str:
    """ save avatar """
    (useless, ext) = os.path.splitext(filename)
    if ext is None or data is None:
        # 417 - Expectation Failed
        msg = 'Expectation Failed'
        return render_template('response.html', code=417, message=msg, filename=filename)
    ext = ext.replace('.', '').lower()
    if ext not in IMAGE_FILE_TYPES:
        # 415 - Unsupported Media Type
        msg = 'File extensions not support: %s' % ext
        return render_template('response.html', code=415, message=msg, filename=filename)
    # save it with real filename
    filename = '%s.%s' % (identifier.address, ext)
    save_dir = AVATAR_DIRECTORY
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    path = os.path.join(save_dir, filename)
    with open(path, 'wb') as file:
        count = file.write(data)
    # OK
    if count == len(data):
        # 200 - OK
        return render_template('response.html', code=200, message='OK', filename=filename)
    # 500 - Internal Server Error
    return render_template('response.html', code=500, message='Internal Server Error', filename=filename)


"""
    Flask App
    ~~~~~~~~~
"""


app = Flask(__name__)


@app.route('/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route('/<string:identifier>/upload', methods=['POST'])
def upload(identifier: str) -> str:
    """ upload encrypted data file or avatar """
    # TODO: check identifier
    identifier = dimp.ID(identifier)

    # check file
    file = request.files.get('file')
    if file:
        # uploading encrypted data file
        filename = secure_filename(file.filename)
        data = file.read()
        if data is None or len(data) == 0:
            # 204 - No Content
            return render_template('response.html', code=204, message='No Content', filename=filename)
        # save encrypted data file
        return save_data(data=data, filename=filename, identifier=identifier)

    # check avatar
    avatar_file = request.files.get('avatar')
    if avatar_file:
        # uploading avatar
        filename = secure_filename(avatar_file.filename)
        data = avatar_file.read()
        if data is None or len(data) == 0:
            # 204 - No Content
            return render_template('response.html', code=204, message='No Content', filename=filename)
        # save avatar
        return save_avatar(data=data, filename=filename, identifier=identifier)

    # 400 - Bad Request
    return render_template('response.html', code=400, message='Bad Request')


@app.route('/download/<string:identifier>/<path:filename>', methods=['GET'])
def download(identifier: str, filename: str) -> str:
    """ response file data as attachment """
    identifier = dimp.ID(identifier)
    filename = secure_filename(filename)
    save_dir = os.path.join(UPLOAD_DIRECTORY, identifier.address)
    return send_from_directory(save_dir, filename, as_attachment=True)


@app.route('/avatar/<string:identifier>.<string:ext>', methods=['GET'])
@app.route('/<string:identifier>/avatar.<string:ext>', methods=['GET'])
def avatar(identifier: str, ext: str) -> str:
    """ response avatar file as attachment """
    identifier = dimp.ID(identifier)
    ext = secure_filename(ext)
    filename = '%s.%s' % (identifier.address, ext)
    save_dir = AVATAR_DIRECTORY
    return send_from_directory(save_dir, filename, as_attachment=False)


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=True)
