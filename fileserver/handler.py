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

import os
from typing import Optional, Tuple, Set, List

from werkzeug.utils import secure_filename
from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS

from dimples import md5, hex_encode, hex_decode
from dimples import ID

from fileserver.shared import GlobalVariable


shared = GlobalVariable()


def get_extension(filename: str) -> Optional[str]:
    _, ext = os.path.splitext(filename)
    if ext is not None:
        return ext.replace('.', '').lower()


def get_filename(data: bytes, ext: str) -> str:
    """ :return: {MD5(data)}.ext """
    return '%s.%s' % (hex_encode(md5(data)), ext)


def get_avatar_directory(identifier: ID) -> str:
    """ :return: /data/dim/avatars/{ADDRESS} """
    return os.path.join(shared.avatar_directory, str(identifier.address))


def get_upload_directory(identifier: ID) -> str:
    """ :return: /data/dim/uploads/{ADDRESS} """
    return os.path.join(shared.upload_directory, str(identifier.address))


def save_file(data: bytes, filename: str, file_types: Set[str], directory: str) -> Tuple[int, str, str]:
    """ :return: code, msg, filename """
    ext = get_extension(filename=filename)
    if ext is None:
        # 417 - Expectation Failed
        msg = 'Expectation Failed'
        return 417, msg, filename
    elif ext not in file_types:
        # 415 - Unsupported Media Type
        msg = 'File extensions not support: %s' % ext
        return 415, msg, filename
    # save it with real filename
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = get_filename(data=data, ext=ext)
    path = os.path.join(directory, filename)
    with open(path, 'wb') as file:
        count = file.write(data)
    # OK
    if count == len(data):
        # 200 - OK
        return 200, 'OK', filename
    else:
        # 500 - Internal Server Error
        return 500, 'Internal Server Error', filename


def fetch_secret(secrets: List[str], enigma: Optional[str]) -> Optional[bytes]:
    """ decode the secret starts with enigma """
    assert len(secrets) > 0, 'secrets not found'
    if enigma is None:
        # enigma not found, decode the first one
        return hex_decode(string=secrets[0])
    # search by enigma
    for item in secrets:
        if item.startswith(enigma):
            # decode the item starts with enigma
            return hex_decode(string=item)


"""
    Flask App
    ~~~~~~~~~
"""


app = Flask(__name__)

CORS(app, origins=['localhost:*'])


@app.route('/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route('/<string:identifier>/upload', methods=['POST'])
def upload(identifier: str) -> str:
    """ upload encrypted data file or avatar """
    # 1. get file data
    encrypted_file = request.files.get('file')
    if encrypted_file is not None:
        data = encrypted_file.read()
        filename = encrypted_file.filename
    else:
        avatar_file = request.files.get('avatar')
        if avatar_file is not None:
            data = avatar_file.read()
            filename = avatar_file.filename
        else:
            data = None
            filename = None
    if filename is None or len(filename) == 0:
        # 400 - Bad Request
        return render_template('error.html', code=400, message='Bad Request')
    data_size = 0 if data is None else len(data)
    if data_size <= 0:
        # 204 - No Content
        return render_template('error.html', code=204, message='No Content')
    elif data_size > shared.allowed_file_size:
        # 403 - Forbidden
        return render_template('error.html', code=403, message='Forbidden')
    # 2. check digest
    enigma = request.args.get('enigma')     # leading 6 chars of hex(md5_secret)
    digest_salt = request.args.get('salt')  # random bytes by client
    digest_value = request.args.get('md5')  # md5(data + secret + salt)
    uid = ID.parse(identifier=identifier)
    if digest_salt is None or digest_value is None or uid is None:
        # 400 - Bad Request
        return render_template('error.html', code=400, message='Bad Request')
    md5_secret = fetch_secret(secrets=shared.md5_secrets, enigma=enigma)
    digest_salt = hex_decode(string=digest_salt)
    digest_value = hex_decode(string=digest_value)
    if md5_secret is None or digest_salt is None:
        # 403 - Forbidden
        return render_template('error.html', code=403, message='Forbidden')
    # md5(data + secret + salt)
    if digest_value != md5(data=(data + md5_secret + digest_salt)):
        # 401 - Unauthorized
        return render_template('error.html', code=401, message='Unauthorized')
    # 3. save file data
    if encrypted_file is not None:
        # save encrypted data file
        file_types = shared.allowed_file_types
        directory = get_upload_directory(identifier=uid)
        url = shared.download_url
    else:
        # save avatar
        file_types = shared.image_file_types
        directory = get_avatar_directory(identifier=uid)
        url = shared.avatar_url
    # filename = secure_filename(filename=filename)
    code, msg, name = save_file(data=data, filename=filename, file_types=file_types, directory=directory)
    if code != 200:
        return render_template('error.html', code=code, message=msg)
    # OK!
    url = url.replace('{ID}', identifier)
    url = url.replace('{FILENAME}', name)
    return render_template('success.html', code=code, message=msg, filename=name, url=url)


@app.route('/download/<string:identifier>/<path:filename>', methods=['GET'])
def download(identifier: str, filename: str) -> str:
    """ response file data as attachment """
    uid = ID.parse(identifier=identifier)
    if uid is None or filename is None:
        return render_template('error.html', code=400, message='Bad Request')
    # send from directory
    directory = get_upload_directory(identifier=uid)
    filename = secure_filename(filename)
    return send_from_directory(directory, filename, as_attachment=True)


@app.route('/avatar/<string:identifier>/<path:filename>', methods=['GET'])
def avatar(identifier: str, filename: str) -> str:
    """ response avatar file as attachment """
    uid = ID.parse(identifier=identifier)
    if uid is None or filename is None:
        return render_template('error.html', code=400, message='Bad Request')
    # send from directory
    directory = get_avatar_directory(identifier=uid)
    filename = secure_filename(filename)
    return send_from_directory(directory, filename, as_attachment=False)
