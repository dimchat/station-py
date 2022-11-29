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

from typing import Optional, List

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import DocumentCommand
from dimsdk import ForwardContent
from dimsdk import DocumentCommandProcessor as SuperCommandProcessor

from ...database import Database


g_database = Database()


class DocumentCommandProcessor(SuperCommandProcessor):

    def __check_login(self, identifier: ID, sender: ID) -> Optional[ReliableMessage]:
        cmd, msg = g_database.login_info(identifier=identifier)
        if cmd is not None:
            if sender.type == EntityType.STATION:
                # this is a request from another station.
                # if the user is not roaming to this station, just ignore it,
                # let the target station to respond.
                facebook = self.facebook
                # from ...common import CommonFacebook
                # assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
                srv = facebook.current_user
                if sender == srv.identifier:
                    # the station is querying itself, ignore it
                    return None
                # get roaming station ID
                station = cmd.station
                # assert isinstance(station, dict), 'login command error: %s' % cmd
                sid = ID.parse(identifier=station.get('ID'))
                if sid != srv.identifier:
                    # not my guest, ignore it.
                    return None
            return msg

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, DocumentCommand), 'command error: %s' % content
        responses = super().process(content=content, msg=msg)
        if content.document is not None:
            return responses
        for res in responses:
            if isinstance(res, DocumentCommand):
                # this is a request, and target document got.
                sender = msg.sender
                if sender.type == EntityType.BOT:
                    # no need to respond LoginCommand message to a bot,
                    # just DocumentCommand is OK
                    return responses
                # check login command message
                login = self.__check_login(identifier=content.identifier, sender=sender)
                if login is not None:
                    # respond login command
                    responses.append(ForwardContent.create(message=login))
        return responses
