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
    Terminal
    ~~~~~~~~

    Local User
"""

import json

from dimp import ID, NetworkID, LocalUser, Group
from dimp import Content, Command, MetaCommand, ProfileCommand, HistoryCommand, GroupCommand
from dimp import InstantMessage, ReliableMessage

from ..common import Facebook, Messenger

from .connection import IConnectionDelegate


def id_list(members: list, facebook: Facebook) -> list:
    array = []
    for item in members:
        array.append(facebook.identifier(item))
    return array


def is_founder(member: ID, group: Group, facebook: Facebook) -> bool:
    founder = group.founder
    if founder is not None:
        return founder == member
    if group.meta is not None:
        meta = facebook.meta(identifier=member)
        if meta is not None:
            return group.meta.match_public_key(meta.key)


def exists_member(member: ID, group: Group) -> bool:
    owner = group.owner
    if owner is not None and owner == member:
        return True
    members = group.members
    if members is not None:
        return member in members


class Terminal(LocalUser, IConnectionDelegate):

    def __init__(self, identifier: ID):
        super().__init__(identifier=identifier)
        self.messenger: Messenger = None

    def send_content(self, content: Content, receiver: ID) -> bool:
        """ Send message content to receiver """
        # check meta
        if not receiver.is_broadcast:
            meta = self.delegate.meta(identifier=receiver)
            if meta is None:
                # NOTICE: if meta for sender not found,
                #         the client will query it automatically
                # TODO: save the message content in waiting queue
                return False
        # check group message
        if receiver.type.is_group():
            content.group = receiver
        # create InstantMessage
        i_msg = InstantMessage.new(content=content, sender=self.identifier, receiver=receiver)
        # send out after encrypt and sign
        return self.messenger.send_message(msg=i_msg, split=True)

    def __process_query(self, group: Group, commander: ID) -> bool:
        # 0. check permission
        if not exists_member(member=commander, group=group):
            # only member can query
            return False
        # 1. get members
        members = group.members
        if members is None or len(members) == 0:
            return False
        # 2. response all members to the sender
        invite = GroupCommand.invite(group=group.identifier, members=members)
        return self.send_content(content=invite, receiver=commander)

    def __process_reset(self, group: Group, commander: ID, members: list) -> bool:
        facebook: Facebook = self.delegate
        # 0. check permission
        if group.founder != commander:
            # only founder can reset group members
            grp_meta = group.meta
            meta = facebook.meta(identifier=commander)
            if grp_meta is None or meta is None or not grp_meta.match_public_key(meta.key):
                return False
        elif members is None or len(members) == 0:
            # command error?
            return False
        # replace items with ID objects
        members = id_list(members=members, facebook=facebook)
        # save new members list
        return facebook.save_members(members=members, identifier=group.identifier)

    def __process_invite(self, group: Group, commander: ID, members: list) -> bool:
        facebook: Facebook = self.delegate
        existed = group.members
        # 0. check permission
        if group.founder is None and (existed is None or len(existed) == 0):
            # FIXME: group profile lost?
            # FIXME: how to avoid strangers impersonating group members?
            pass
        elif members is None or len(members) == 0:
            # command error?
            return False
        elif not exists_member(member=commander, group=group):
            # only member can invite
            return False
        # replace items with ID objects
        members = id_list(members=members, facebook=facebook)
        # 1. check founder for reset command
        if is_founder(member=commander, group=group, facebook=facebook):
            for item in members:
                if is_founder(member=item, group=group, facebook=facebook):
                    # invite founder? it means this should be a 'reset' command
                    return self.__process_reset(group=group, commander=commander, members=members)
        # 2. check added member(s)
        if existed is None:
            existed = []
        count = 0
        for item in members:
            if item not in existed:
                existed.append(item)
                count += 1
        if count > 0:
            # save new members list
            return facebook.save_members(members=existed, identifier=group.identifier)

    def __process_expel(self, group: Group, commander: ID, members: list) -> bool:
        facebook: Facebook = self.delegate
        # 0. check permission
        if group.founder != commander:
            # only founder can expel member
            return False
        elif members is None or len(members) == 0:
            # command error?
            return False
        existed = group.members
        if existed is None or len(existed) == 0:
            return False
        # replace items with ID objects
        members = id_list(members=members, facebook=facebook)
        # remove IDs from existed members
        count = 0
        for item in members:
            if item in existed:
                existed.remove(item)
                count += 1
        if count > 0:
            # save new members list
            return facebook.save_members(members=existed, identifier=group.identifier)

    def __process_quit(self, group: Group, commander: ID) -> bool:
        facebook: Facebook = self.delegate
        # 0. check permission
        if group.founder == commander:
            # founder cannot quit
            return False
        elif not exists_member(member=commander, group=group):
            # not a member yet
            return False
        existed = group.members
        if existed is None or len(existed) == 0:
            return False
        if commander in existed:
            existed.remove(commander)
            # save new members list
            return facebook.save_members(members=existed, identifier=group.identifier)

    def process(self, cmd: Command, sender: ID) -> bool:
        """Process group history

            :param cmd - group command
            :param sender - commander
            :return True on success
        """
        assert sender.valid, 'sender error: %s' % sender
        facebook: Facebook = self.delegate
        command = cmd.command
        #
        #  system commands
        #
        if 'meta' == command:
            cmd = MetaCommand(cmd)
            identifier = facebook.identifier(cmd.identifier)
            # save meta
            meta = cmd.meta
            if facebook.verify_meta(meta=meta, identifier=identifier):
                ok = facebook.save_meta(meta=meta, identifier=identifier)
            else:
                ok = False
            return ok
        elif 'profile' == command:
            cmd = ProfileCommand(cmd)
            identifier = facebook.identifier(cmd.identifier)
            # save meta
            meta = cmd.meta
            if facebook.verify_meta(meta=meta, identifier=identifier):
                ok1 = facebook.save_meta(meta=meta, identifier=identifier)
            else:
                ok1 = False
            # save profile
            profile = cmd.profile
            if facebook.verify_profile(profile=profile):
                ok2 = facebook.save_profile(profile=profile)
            else:
                ok2 = False
            return ok1 and ok2
        #
        #  group commands
        #
        group = cmd.group
        if group is None:
            # TODO: only group command now
            return False
        facebook: Facebook = self.delegate
        group = facebook.identifier(group)
        if group.type.value != NetworkID.Polylogue:
            # TODO: only Polylogue supported now
            return False
        members = cmd.get('members')
        if members is None:
            member = cmd.get('member')
            if member is not None:
                members = [member]
        polylogue = facebook.group(identifier=group)
        if polylogue is None:
            # TODO: query group meta form DIM network
            return False
        if GroupCommand.INVITE == command:
            return self.__process_invite(group=polylogue, commander=sender, members=members)
        elif GroupCommand.EXPEL == command:
            return self.__process_expel(group=polylogue, commander=sender, members=members)
        elif GroupCommand.QUIT == command:
            return self.__process_quit(group=polylogue, commander=sender)
        elif GroupCommand.QUERY == command:
            return self.__process_query(group=polylogue, commander=sender)
        elif GroupCommand.RESET == command:
            return self.__process_reset(group=polylogue, commander=sender, members=members)

    def receive_message(self, msg: InstantMessage) -> bool:
        """Receive instant message

            :param msg - instant message
            :return True on correct
        """
        pass

    def process_message(self, msg: ReliableMessage) -> bool:
        # verify and decrypt
        i_msg: InstantMessage = self.messenger.verify_decrypt(msg=msg)
        if i_msg is None:
            raise ValueError('failed to verify/decrypt message: %s' % msg)
        facebook: Facebook = self.delegate
        sender = facebook.identifier(i_msg.envelope.sender)
        content = i_msg.content
        # check meta for new group ID
        gid = content.group
        if gid is not None:
            gid = facebook.identifier(gid)
            if not gid.is_broadcast:
                # check meta
                meta = facebook.meta(identifier=gid)
                if meta is None:
                    # NOTICE: if meta for group not found,
                    #         the client will query it automatically
                    # TODO: insert the message to a temporary queue to waiting meta
                    return False
            # check whether the group members info needs update
            group = facebook.group(identifier=gid)
            # if the group info not found, and this is not an 'invite' command
            #     query group info from the sender
            needs_update = group.founder is None
            if isinstance(content, HistoryCommand):
                if GroupCommand.INVITE == content.command:
                    # FIXME: can we trust this stranger?
                    #        may be we should keep this members list temporary,
                    #        and send 'query' to the founder immediately.
                    # TODO: check whether the members list is a full list,
                    #       it should contain the group owner(founder)
                    needs_update = False
            if needs_update:
                query = GroupCommand.query(group=gid)
                self.send_content(content=query, receiver=sender)
        # process command
        if isinstance(content, Command):
            return self.process(cmd=content, sender=sender)
        else:
            return self.receive_message(msg=i_msg)

    #
    #  IConnectionDelegate
    #
    def receive_package(self, data: bytes):
        """ Receive data package """
        try:
            # deserialize message
            r_msg = self.messenger.deserialize_message(data=data)
            # process message
            self.process_message(r_msg)
        except UnicodeDecodeError as error:
            print('Terminal > decode error: %s' % error)
        except ValueError as error:
            print('Terminal > value error: %s, package: %s' % (error, data))
