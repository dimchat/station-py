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
    Group bot: 'assistant'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for collecting and responding group member list
"""

import threading
import time

from dimp import ID, Group
from dimp import Content, TextContent
from dimp import MetaCommand, ProfileCommand, GroupCommand, InviteCommand

from libs.common import Log, Messenger

from robots.config import g_facebook
from robots.config import group_naruto, load_freshmen


class FreshmenScanner(threading.Thread):

    def __init__(self):
        super().__init__()
        # delegate for send message
        self.messenger: Messenger = None
        # group
        gid = g_facebook.identifier(group_naruto)
        self.__group: Group = g_facebook.group(gid)

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    def __send_content(self, content: Content, receiver: ID) -> bool:
        return self.messenger.send_content(content=content, receiver=receiver)

    def __freshmen(self) -> list:
        freshmen = load_freshmen()
        if freshmen is None:
            return []
        # remove existed members
        members = self.__members()
        for item in members:
            if item in freshmen:
                freshmen.remove(item)
        users = []
        for item in freshmen:
            profile = g_facebook.profile(identifier=item)
            if profile is None:
                # profile not found
                continue
            if 'data' not in profile:
                # profile empty
                continue
            # profile OK
            users.append(item)
        self.info('got freshmen: %s from %s' % (users, freshmen))
        return users

    def __members(self) -> list:
        members = self.__group.members
        if members is None:
            return []
        self.info('got %d member(s) in group: %s' % (len(members), self.__group))
        return members

    def __save_members(self, members: list) -> bool:
        gid = self.__group.identifier
        # TODO: check permission (whether myself in this group)
        return g_facebook.save_members(members=members, identifier=gid)

    def __response_meta(self) -> MetaCommand:
        gid = self.__group.identifier
        meta = self.__group.meta
        profile = self.__group.profile
        if profile is None:
            cmd = MetaCommand.response(identifier=gid, meta=meta)
        else:
            cmd = ProfileCommand.response(identifier=gid, profile=profile, meta=meta)
        return cmd

    def __invite_members(self, members: list) -> InviteCommand:
        gid = self.__group.identifier
        return GroupCommand.invite(group=gid, members=members)

    def __welcome(self, freshmen: list) -> TextContent:
        names = [g_facebook.nickname(item) for item in freshmen]
        count = len(names)
        if count == 1:
            string = names[0]
            msg = 'Welcome new member~ %s.' % string
        elif count > 1:
            string = ', '.join(names)
            msg = 'Welcome new members~ %s.' % string
        else:
            # should not be here
            msg = 'Welcome!'
        text = TextContent.new(text=msg)
        text.group = self.__group.identifier
        return text

    def run(self):
        while True:
            time.sleep(30)
            #
            #  1. get freshmen and group members
            #
            freshmen = self.__freshmen()
            if len(freshmen) == 0:
                continue
            self.info('freshmen: %s' % freshmen)
            members = self.__members()
            self.info('group members: %s' % members)
            #
            #  2. send 'invite' command to existed members
            #
            cmd = self.__invite_members(members=freshmen)
            for item in members:
                self.__send_content(content=cmd, receiver=item)
            self.info('invite command sent: %s' % cmd)
            #
            #  3. update group members
            #
            for item in freshmen:
                # add freshmen to members
                if item not in members:
                    members.append(item)
            if self.__save_members(members=members):
                self.info('group members updated: %s' % members)
            #
            #  4.1. send group meta to all freshmen
            #
            cmd = self.__response_meta()
            for item in freshmen:
                self.__send_content(content=cmd, receiver=item)
            self.info('group meta/profile sent: %s' % cmd)
            #
            #  4.2. send 'invite' command to all freshmen
            #
            cmd = self.__invite_members(members=members)
            for item in freshmen:
                self.__send_content(content=cmd, receiver=item)
            self.info('invite command sent: %s' % cmd)
            #
            #  5. Welcome!
            #
            text = self.__welcome(freshmen=freshmen)
            gid = self.__group.identifier
            self.__send_content(content=text, receiver=gid)
            self.info('Welcome sent to %s: %s' % (gid, text))
