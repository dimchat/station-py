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
    Command Processor for 'search'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    search users with keyword(s)
"""

from dimp import ID
from dimp import Content
from dimp import Command

from .cpu import CPU


class SearchCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        self.info('search users for %s, %s' % (sender, cmd))
        # keywords
        keywords = cmd.get('keywords')
        if keywords is None:
            keywords = cmd.get('keyword')
            if keywords is None:
                keywords = cmd.get('kw')
        # search for each keyword
        if keywords is None:
            keywords = []
        else:
            keywords = keywords.split(' ')
        results = self.database.search(keywords=keywords)
        # response
        users = list(results.keys())
        response = Command.new(command='search')
        response['message'] = '%d user(s) found' % len(users)
        response['users'] = users
        response['results'] = results
        return response
