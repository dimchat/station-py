# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Report Protocol
    ~~~~~~~~~~~~~~~

    Report for online/offline, ...
"""

from typing import Optional

from dimp import Command


class ReportCommand(Command):
    """
        Report Command
        ~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            command  : "report",
            title    : "online",   // or "offline"
            time     : 1234567890
        }
    """

    REPORT = 'report'

    ONLINE = 'online'
    OFFLINE = 'offline'

    def __init__(self, cmd: Optional[dict] = None, title: Optional[str] = None):
        if cmd is None:
            super().__init__(command=ReportCommand.REPORT)
        else:
            super().__init__(cmd=cmd)
        if title is not None:
            self['title'] = title

    #
    #   report title
    #
    @property
    def title(self) -> str:
        return self.get('title')

    @title.setter
    def title(self, value: str):
        self['title'] = value
