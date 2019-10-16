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
    Message Processor
    ~~~~~~~~~~~~~~~~~

    Message processor for Request Handler
"""

from dimp import ID, Profile
from dimp import ContentType, Content, TextContent, Command
from dimp import HandshakeCommand, ProfileCommand, MetaCommand, ReceiptCommand
from dimp import InstantMessage

from common import Log
from common import Session, Server

from etc.cfg_gsp import station_name

from .dialog import Dialog
from .config import g_facebook, g_database, g_session_server, g_receptionist, g_monitor


class MessageProcessor:

    def __init__(self, request_handler):
        super().__init__()
        self.request_handler = request_handler
        self.dialog: Dialog = None

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    @property
    def client_address(self) -> str:
        return self.request_handler.client_address

    @property
    def identifier(self) -> ID:
        return self.request_handler.identifier

    @property
    def station(self) -> Server:
        return self.request_handler.station

    def current_session(self, identifier: ID=None) -> Session:
        return self.request_handler.current_session(identifier=identifier)

    def check_session(self, identifier: ID) -> Content:
        return self.request_handler.check_session(identifier=identifier)

    """
        main entrance
    """
    def process(self, msg: InstantMessage) -> Content:
        # try to decrypt message
        sender = g_facebook.identifier(msg.envelope.sender)
        content = msg.content
        # the client is talking with station (handshake, search users, get meta/profile, ...)
        if content.type == ContentType.Command:
            self.info('command from client %s, %s' % (self.client_address, content))
            return self.process_command(content=content, sender=sender)
        # talk with station?
        self.info('message from client %s, %s' % (self.client_address, content))
        return self.process_dialog(content=content, sender=sender)

    def process_dialog(self, content: Content, sender: ID) -> Content:
        if self.dialog is None:
            self.dialog = Dialog()
        self.info('@@@ call NLP and response to the client %s, %s' % (self.client_address, sender))
        return self.dialog.talk(content=content, sender=sender)

    def process_command(self, content: Content, sender: ID) -> Content:
        command = content['command']
        if 'handshake' == command:
            # handshake protocol
            return self.process_handshake(sender=sender, cmd=HandshakeCommand(content))
        if 'meta' == command:
            # meta protocol
            return self.process_meta_command(cmd=MetaCommand(content))
        if 'profile' == command:
            # profile protocol
            return self.process_profile_command(cmd=ProfileCommand(content))
        # check session valid
        handshake = self.check_session(identifier=sender)
        if handshake is not None:
            return handshake
        # commands after handshake accepted
        if 'login' == command:
            # login protocol
            return self.process_login_command(cmd=Command(content))
        if 'contacts' == command:
            # storage protocol: post/get contacts
            return self.process_contacts_command(cmd=Command(content), sender=sender)
        if 'members' == command:
            # storage protocol: post/get groups
            return self.process_group_command(cmd=Command(content), sender=sender)
        if 'users' == command:
            # show online users (connected)
            return self.process_users_command()
        if 'search' == command:
            # search users with keyword(s)
            return self.process_search_command(cmd=Command(content))
        if 'broadcast' == command or 'report' == command:
            # broadcast or report
            return self.process_broadcast_command(cmd=Command(content))
        # error
        self.error('unknown command %s' % content)

    def process_handshake(self, sender: ID, cmd: HandshakeCommand=None) -> Content:
        # set/update session in session server with new session key
        self.info('handshake with client %s, %s' % (self.client_address, sender))
        if cmd is None:
            session_key = None
        else:
            session_key = cmd.session
        session = self.current_session(identifier=sender)
        if session_key == session.session_key:
            # session verified success
            session.valid = True
            session.active = True
            nickname = g_facebook.nickname(identifier=sender)
            cli = self.client_address
            self.info('handshake accepted %s %s %s, %s' % (nickname, cli, sender, session_key))
            g_monitor.report(message='User %s logged in %s %s' % (nickname, cli, sender))
            # add the new guest for checking offline messages
            g_receptionist.add_guest(identifier=sender)
            return HandshakeCommand.success()
        else:
            # session key not match, ask client to sign it with the new session key
            return HandshakeCommand.again(session=session.session_key)

    def process_meta_command(self, cmd: MetaCommand) -> Content:
        identifier = cmd.identifier
        meta = cmd.meta
        if meta is not None:
            # received a meta for ID
            self.info('received meta %s' % identifier)
            if g_facebook.save_meta(identifier=identifier, meta=meta):
                self.info('meta saved %s, %s' % (identifier, meta))
                return ReceiptCommand.receipt(message='Meta for %s received!' % identifier)
            else:
                self.error('meta not match %s, %s' % (identifier, meta))
                return TextContent.new(text='Meta not match %s!' % identifier)
        # querying meta for ID
        self.info('search meta %s' % identifier)
        meta = g_facebook.meta(identifier=identifier)
        # response
        if meta is not None:
            return MetaCommand.response(identifier=identifier, meta=meta)
        else:
            return TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    def process_profile_command(self, cmd: ProfileCommand) -> Content:
        identifier = cmd.identifier
        meta = cmd.meta
        if meta is not None:
            # received a meta for ID
            if g_facebook.save_meta(identifier=identifier, meta=meta):
                self.info('meta saved %s, %s' % (identifier, meta))
            else:
                self.error('meta not match %s, %s' % (identifier, meta))
                return TextContent.new(text='Meta not match %s!' % identifier)
        profile = cmd.profile
        if profile is not None:
            # received a new profile for ID
            self.info('received profile %s' % identifier)
            if g_facebook.save_profile(profile=profile):
                self.info('profile saved %s' % profile)
                return ReceiptCommand.receipt(message='Profile of %s received!' % identifier)
            else:
                self.error('profile not valid %s' % profile)
                return TextContent.new(text='Profile signature not match %s!' % identifier)
        # querying profile for ID
        self.info('search profile %s' % identifier)
        profile = g_facebook.profile(identifier=identifier)
        if identifier == self.station.identifier:
            # querying profile of current station
            private_key = g_facebook.private_key_for_signature(identifier=identifier)
            if private_key is not None:
                if profile is None:
                    profile = Profile.new(identifier=identifier)
                # NOTICE: maybe the station manager config different station with same ID,
                #         or the client query different station with same ID,
                #         so we need to correct station name here
                profile.name = station_name
                profile.sign(private_key=private_key)
        # response
        if profile is not None:
            return ProfileCommand.response(identifier=identifier, profile=profile)
        else:
            return TextContent.new(text='Sorry, profile for %s not found.' % identifier)

    def process_group_command(self, cmd: Command, sender: ID) -> Content:

        if 'group' not in cmd:
            return TextContent.new(text='Sorry, need group identifier.' % sender)

        group_identifier = cmd['group']
        # query members, load it
        self.info('search members for %s' % group_identifier)
        stored: Command = g_facebook.members(identifier=group_identifier)
        # response
        if stored is not None:
            # response the stored group members command directly
            return stored
        else:
            return TextContent.new(text='Sorry, group of %s not found.' % group_identifier)

    def process_contacts_command(self, cmd: Command, sender: ID) -> Content:
        if 'data' in cmd or 'contacts' in cmd:
            # receive encrypted contacts, save it
            if g_facebook.save_contacts_command(cmd=cmd, sender=sender):
                self.info('contacts command saved for %s' % sender)
                return ReceiptCommand.receipt(message='Contacts of %s received!' % sender)
            else:
                self.error('failed to save contacts command: %s' % cmd)
                return TextContent.new(text='Contacts not stored %s!' % cmd)
        # query encrypted contacts, load it
        self.info('search contacts(command with encrypted data) for %s' % sender)
        stored: Command = g_facebook.contacts_command(identifier=sender)
        # response
        if stored is not None:
            # response the stored contacts command directly
            return stored
        else:
            return TextContent.new(text='Sorry, contacts of %s not found.' % sender)

    def process_login_command(self, cmd: Command) -> Content:
        # TODO: update login status and return nothing
        pass

    def process_users_command(self) -> Content:
        self.info('get online user(s) for %s' % self.identifier)
        users = g_session_server.random_users(max_count=20)
        response = Command.new(command='users')
        response['message'] = '%d user(s) connected' % len(users)
        response['users'] = users
        return response

    def process_search_command(self, cmd: Command) -> Content:
        self.info('search users for %s, %s' % (self.identifier, cmd))
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
        results = g_database.search(keywords=keywords)
        # response
        users = list(results.keys())
        response = Command.new(command='search')
        response['message'] = '%d user(s) found' % len(users)
        response['users'] = users
        response['results'] = results
        return response

    def process_broadcast_command(self, cmd: Command) -> Content:
        self.info('client broadcast %s, %s' % (self.identifier, cmd))
        title = cmd.get('title')
        if 'apns' == title:
            # submit device token for APNs
            token = cmd.get('device_token')
            self.info('client report token %s' % token)
            if token is not None:
                g_database.save_device_token(token=token, identifier=self.identifier)
                return ReceiptCommand.receipt(message='Token received')
        if 'online' == title:
            # welcome back!
            self.info('client online')
            session = self.current_session()
            g_receptionist.add_guest(identifier=session.identifier)
            session.active = True
            return ReceiptCommand.receipt(message='Client online received')
        if 'offline' == title:
            # goodbye!
            self.info('client offline')
            session = self.current_session()
            session.active = False
            return ReceiptCommand.receipt(message='Client offline received')
        if 'report' == title:
            # compatible with v1.0
            state = cmd.get('state')
            self.info('client report state %s' % state)
            if state is not None:
                session = self.current_session()
                if 'background' == state:
                    session.active = False
                elif 'foreground' == state:
                    # welcome back!
                    g_receptionist.add_guest(identifier=session.identifier)
                    session.active = True
                else:
                    self.error('unknown state %s' % state)
                    session.active = True
                return ReceiptCommand.receipt(message='Client state received')
        # error
        self.error('unknown broadcast command %s' % cmd)
