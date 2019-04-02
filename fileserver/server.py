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

from werkzeug.utils import secure_filename
from flask import Flask, request, send_from_directory, render_template

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from fileserver.librarian import FileManager

HOST = '0.0.0.0'
PORT = 8081

# UPLOAD_DIRECTORY = '/tmp/www/uploads'
UPLOAD_DIRECTORY = '/data/.dim/uploads'

ALLOWED_FILE_TYPE = {'png', 'jpg', 'jpeg', 'gif'}

file_manager = FileManager(base_dir=UPLOAD_DIRECTORY)
file_manager.extensions = ALLOWED_FILE_TYPE

app = Flask(__name__)


@app.route('/test.html', methods=['GET'])
def test() -> str:
    return render_template('test.html')


@app.route('/<string:sender>/upload', methods=['POST'])
def upload(sender: str) -> str:
    # 1. get file data
    file = request.files['file']
    if file is None:
        # 400 - Bad Request
        return render_template('response.html', command='upload', code=400, message='Bad Request')
    filename = secure_filename(file.filename)
    data = file.read()
    if data is None or len(data) == 0:
        # 204 - No Content
        return render_template('response.html', command='upload', code=204, message='No Content', filename=filename)
    # save file
    try:
        file_manager.save(data=data, filename=filename, sender=sender)
    except TypeError as error:
        # not supported file type
        return render_template('response.html', command='upload', code=415, message=error, filename=filename)
    except AssertionError as error:
        # filename or data cannot be empty
        return render_template('response.html', command='upload', code=204, message=error, filename=filename)
    # 200 - OK
    return render_template('response.html', command='upload', code=200, message='OK', filename=filename)


@app.route('/download/<string:sender>/<path:filename>', methods=['GET'])
def download(sender: str, filename: str) -> str:
    filename = secure_filename(filename)
    # check file exists
    path = file_manager.path(filename=filename, sender=sender)
    if not os.path.isfile(path):
        # 404 - Not Found
        return render_template('response.html', command='download', code=404, message='Not Found', filename=filename)
    # response file data as attachment
    directory = file_manager.directory(sender=sender)
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=True)
