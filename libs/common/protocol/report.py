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

    def __new__(cls, cmd: dict):
        """
        Create report command

        :param cmd: command info
        :return: ReportCommand object
        """
        if cmd is None:
            return None
        elif cls is ReportCommand:
            if isinstance(cmd, ReportCommand):
                # return ReportCommand object directly
                return cmd
        # new ReportCommand(dict)
        return super().__new__(cls, cmd)

    def __init__(self, content: dict):
        if self is content:
            # no need to init again
            return
        super().__init__(content)

    #
    #   report title
    #
    @property
    def title(self) -> str:
        return self.get('title')

    @title.setter
    def title(self, value: str):
        self['title'] = value

    #
    #   Factories
    #
    @classmethod
    def new(cls, content: dict=None, title: str=None, time: int=0):
        """
        Create report command

        :param content: command info
        :param title:   report title
        :param time:    command time
        :return: ReportCommand object
        """
        if content is None:
            # create empty content
            content = {}
        # new ReportCommand(dict)
        if title is None:
            content['title'] = title
        return super().new(content=content, command=cls.REPORT, time=time)


# register command class
Command.register(command=ReportCommand.REPORT, command_class=ReportCommand)
Command.register(command=ReportCommand.ONLINE, command_class=ReportCommand)
Command.register(command=ReportCommand.OFFLINE, command_class=ReportCommand)
