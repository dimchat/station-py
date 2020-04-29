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

from flask import Response, render_template

from .config import BASE_URL
from .config import respond_xml
from .config import g_facebook, app
from .worker import Worker

g_worker = Worker(facebook=g_facebook)


@app.route(BASE_URL+'/', methods=['GET'])
def index() -> Response:
    users = g_worker.outlines()
    xml = render_template('users.opml', users=users)
    return respond_xml(xml)


@app.route(BASE_URL+'/<string:address>.rss', methods=['GET'])
def rss(address: str) -> Response:
    user = g_worker.user_info(address=address)
    # TODO: user is None?
    identifier = g_facebook.identifier(user.get('ID'))
    messages = g_worker.messages(identifier)
    xml = render_template('msgs.rss', user=user, messages=messages)
    return respond_xml(xml)


@app.route(BASE_URL+'/<int:year>/<int:mon>/<int:day>/<string:sig>.xml', methods=['GET'])
def message(sig: str, year: int, mon: int, day: int) -> Response:
    msg = g_worker.message(signature=sig, year=year, month=mon, day=day)
    xml = render_template('msg.xml', msg=msg)
    return respond_xml(xml)
