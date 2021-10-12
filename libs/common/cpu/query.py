# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Query Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. query for group members-list
    2. any existed member or assistant can query group members-list
"""

from typing import List

from dimp import ID
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command, GroupCommand, QueryCommand

from dimsdk import CommandProcessor, GroupCommandProcessor


class QueryCommandProcessor(GroupCommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, QueryCommand), 'group command error: %s' % cmd
        facebook = self.facebook
        group: ID = cmd.group
        # 1. check permission
        if not facebook.exists_member(member=msg.sender, group=group):
            if not facebook.exists_assistant(member=msg.sender, group=group):
                raise AssertionError('only member/assistant can query: %s, %s' % (group, msg.sender))
        # 2. get group members
        members = facebook.members(identifier=group)
        if members is None or len(members) == 0:
            text = 'Group members not found: %s' % group
            return [TextContent(text=text)]
        # 3. response group members for sender
        user = facebook.current_user
        assert user is not None, 'current user not set'
        if facebook.is_owner(member=user.identifier, group=group):
            res = GroupCommand.reset(group=group, members=members)
        else:
            res = GroupCommand.invite(group=group, members=members)
        return [res]


# register
CommandProcessor.register(command=GroupCommand.QUERY, cpu=QueryCommandProcessor())
