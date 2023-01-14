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
    Group Manager
    ~~~~~~~~~~~~~

    This is for sending group message, or managing group members
"""

from typing import Optional, List

from startrek import DeparturePriority

from dimples import ID
from dimples import Content, Command, GroupCommand
from dimples import MetaCommand, DocumentCommand
from dimples.client import ClientMessenger

from ..common import CommonFacebook


class GroupManager:

    def __init__(self, identifier: ID):
        super().__init__()
        self.group: ID = identifier
        self.__messenger: Optional[ClientMessenger] = None

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, value: ClientMessenger):
        self.__messenger = value

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    def send(self, content: Content) -> bool:
        """
        Send message content to this group
        (only existed member can do this)

        :param content: message content
        :return: True on success
        """
        facebook = self.facebook
        messenger = self.messenger
        # check group ID
        gid = content.group
        if gid is None:
            content.group = self.group
        # check members
        members = facebook.members(self.group)
        if members is None or len(members) == 0:
            # get group assistants
            assistants = facebook.assistants(self.group)
            if assistants is None or len(assistants) == 0:
                raise LookupError('failed to get assistant for group: %s' % self.group)
            # querying assistants for group info
            for bot in assistants:
                cmd = GroupCommand.query(group=self.group)
                messenger.send_content(sender=None, receiver=bot, content=cmd)
            return False
        # let group assistant to split and deliver this message to all members
        i_msg, r_msg = messenger.send_content(sender=None, receiver=self.group, content=content)
        return r_msg is not None

    def __send_group_command(self, content: Command, members: List[ID]) -> bool:
        messenger = self.messenger
        ok = True
        for identifier in members:
            if not messenger.send_content(sender=None, receiver=identifier,
                                          content=content, priority=DeparturePriority.NORMAL):
                ok = False
        return ok

    def invite(self, invite_list: List[ID]) -> bool:
        """
        Invite new members to this group
        (only existed member/assistant can do this)

        :param invite_list: new members ID list
        :return: True on success
        """
        facebook = self.facebook
        owner = facebook.owner(self.group)
        assistants = facebook.assistants(self.group)
        members = facebook.members(self.group)
        assert assistants is not None, 'failed to get assistants for group: %s' % self.group

        # 0. send 'meta/document' command to new members
        meta = facebook.meta(self.group)
        doc = facebook.document(identifier=self.group)
        if doc is None or doc.get('data') is None:
            cmd = MetaCommand.response(identifier=self.group, meta=meta)
        else:
            cmd = DocumentCommand.response(document=doc, meta=meta, identifier=self.group)
        self.__send_group_command(content=cmd, members=invite_list)

        # 1. send 'invite' command with new members to existed members
        cmd = GroupCommand.invite(group=self.group, members=invite_list)
        # 1.1. send to existed members
        self.__send_group_command(content=cmd, members=members)
        # 1.2. send to assistants
        self.__send_group_command(content=cmd, members=assistants)
        # 1.3. send to owner
        if owner is not None and owner not in members:
            self.__send_group_command(content=cmd, members=[owner])

        # 2. update local storage
        self.add_members(invite_list)

        # 3. send 'invite' command with all members to new members
        members = facebook.members(self.group)
        cmd = GroupCommand.invite(group=self.group, members=members)
        self.__send_group_command(content=cmd, members=invite_list)
        return True

    def expel(self, expel_list: List[ID]) -> bool:
        """
        Expel members from this group
        (only group owner/assistant can do this)

        :param expel_list: existed member ID list
        :return: True on success
        """
        facebook = self.facebook
        owner = facebook.owner(self.group)
        assistants = facebook.assistants(self.group)
        members = facebook.members(self.group)
        assert owner is not None, 'failed to get owner of group: %s' % self.group
        assert assistants is not None, 'failed to get assistants for group: %s' % self.group
        assert members is not None, 'failed to get members of group: %s' % self.group

        # 0. check members list
        for ass in assistants:
            if ass in expel_list:
                raise AssertionError('Cannot expel group assistants: %s' % ass)
        if owner in expel_list:
            raise AssertionError('Cannot expel group owner: %s' % owner)

        # 1. send 'expel' command to all members
        cmd = GroupCommand.expel(group=self.group, members=expel_list)
        # 1.1. send to existed members
        self.__send_group_command(content=cmd, members=members)
        # 1.2. send to assistants
        self.__send_group_command(content=cmd, members=assistants)
        # 1.3. send to owner
        if owner not in members:
            self.__send_group_command(content=cmd, members=[owner])

        # 2. update local storage
        return self.remove_members(expel_list)

    def quit(self, me: ID) -> bool:
        """
        Quit from this group
        (only group member can do this)

        :param:  me: my ID
        :return: True on success
        """
        facebook = self.facebook
        owner = facebook.owner(self.group)
        assistants = facebook.assistants(self.group)
        members = facebook.members(self.group)
        assert owner is not None, 'failed to get owner of group: %s' % self.group
        assert assistants is not None, 'failed to get assistants for group: %s' % self.group
        assert members is not None, 'failed to get members of group: %s' % self.group

        # 0. check members list
        for ass in assistants:
            if ass == me:
                raise AssertionError('Group assistant cannot quit: %s' % ass)
        if owner == me:
            raise AssertionError('Group owner cannot quit: %s' % owner)

        # 1. send 'quit' command to all members
        cmd = GroupCommand.quit(group=self.group)
        # 1.1. send to existed members
        self.__send_group_command(content=cmd, members=members)
        # 1.2. send to assistants
        self.__send_group_command(content=cmd, members=assistants)
        # 1.3. send to owner
        if owner not in members:
            self.__send_group_command(content=cmd, members=[owner])

        # 2. update local storage
        return self.remove_member(identifier=me)

    #
    #  Local Storage
    #
    def add_members(self, invite_list: List[ID]) -> bool:
        facebook = self.facebook
        members = facebook.members(self.group)
        if members is None:
            raise LookupError('failed to get members for group: %s' % self.group)
        count = 0
        for identifier in invite_list:
            if identifier in members:
                continue
            members.append(identifier)
            count += 1
        if count == 0:
            return False
        return facebook.save_members(members=members, identifier=self.group)

    def remove_members(self, expel_list: List[ID]) -> bool:
        facebook = self.facebook
        members = facebook.members(self.group)
        if members is None:
            raise LookupError('failed to get members for group: %s' % self.group)
        count = 0
        for identifier in expel_list:
            if identifier not in members:
                continue
            members.append(identifier)
            count += 1
        if count == 0:
            return False
        return facebook.save_members(members=members, identifier=self.group)

    def add_member(self, identifier: ID) -> bool:
        return self.add_members([identifier])

    def remove_member(self, identifier: ID) -> bool:
        return self.remove_members([identifier])
