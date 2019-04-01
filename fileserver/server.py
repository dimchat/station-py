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
import hashlib
from binascii import b2a_hex
import json

from flask import Flask, request, send_from_directory, render_template
from werkzeug.utils import secure_filename

HOST = '0.0.0.0'
PORT = 8081

UPLOAD_DIRECTORY = '/tmp/www/uploads'

app = Flask(__name__)


def md5(data) -> str:
    return b2a_hex(hashlib.md5(data).digest()).decode('utf-8')


@app.route('/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route('/upload', methods=['POST'])
def upload() -> str:
    file = request.files['file']
    if file is None:
        return json.dumps({'code': -1, 'message': 'No file uploaded'})
    # get file data
    data = file.read()
    if data is None or len(data) == 0:
        return json.dumps({'code': -2, 'message': 'File data is empty'})
    # get file extension
    filename = file.filename
    if filename is None or '.' not in filename:
        ext = 'png'
    else:
        ext = filename.rsplit('.', 1)[1]
    # save file data
    filename = '%s.%s' % (md5(data), ext)
    path = '%s/%s' % (UPLOAD_DIRECTORY, filename)
    with open(path, 'wb') as file:
        file.write(data)
    return json.dumps({'code': 0, 'message': 'Upload success!', 'filename': filename})


@app.route('/download/<path:filename>')
def download(filename) -> str:
    filename = secure_filename(filename)
    if '.' not in filename:
        filename = filename + '.png'
    path = '%s/%s' % (UPLOAD_DIRECTORY, filename)
    if os.path.isfile(path):
        return send_from_directory(UPLOAD_DIRECTORY, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=True)
