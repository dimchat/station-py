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
    Profile Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional

from dimp import ID, NetworkType
from dimp import ReliableMessage
from dimp import Content
from dimp import ForwardContent, Command, DocumentCommand

from dimsdk import CommandProcessor
from dimsdk import DocumentCommandProcessor as SuperCommandProcessor

from ...database import Database
from ...common import CommonFacebook

from ..messenger import ServerMessenger


g_database = Database()


class DocumentCommandProcessor(SuperCommandProcessor):

    def __check_login(self, identifier: ID, sender: ID) -> Optional[ReliableMessage]:
        cmd, msg = g_database.login_info(identifier=identifier)
        if cmd is not None:
            if sender.type == NetworkType.STATION:
                # this is a request from another station.
                # if the user is not roaming to this station, just ignore it,
                # let the target station to respond.
                facebook = self.facebook
                assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
                srv = facebook.current_user
                if sender == srv.identifier:
                    # the station is querying itself, ignore it
                    return None
                # get roaming station ID
                station = cmd.station
                assert isinstance(station, dict), 'login command error: %s' % cmd
                sid = ID.parse(identifier=station.get('ID'))
                if sid != srv.identifier:
                    # not my guest, ignore it.
                    return None
            return msg

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, DocumentCommand), 'command error: %s' % cmd
        res = super().execute(cmd=cmd, msg=msg)
        if cmd.document is None and isinstance(res, DocumentCommand):
            # this is a request, and target document got.
            # check login command message
            login = self.__check_login(identifier=cmd.identifier, sender=msg.sender)
            if login is not None:
                messenger = self.messenger
                assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
                # respond document
                messenger.send_content(sender=None, receiver=msg.sender, content=res)
                # respond login command
                messenger.send_content(sender=None, receiver=msg.sender, content=ForwardContent(message=login))
                return None
        return res


# register
dpu = DocumentCommandProcessor()
CommandProcessor.register(command=Command.DOCUMENT, cpu=dpu)
CommandProcessor.register(command='profile', cpu=dpu)
CommandProcessor.register(command='visa', cpu=dpu)
CommandProcessor.register(command='bulletin', cpu=dpu)
