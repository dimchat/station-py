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
from dimp import Content, TextContent, Command, HistoryCommand
from dimp import HandshakeCommand, ProfileCommand, MetaCommand
from dimp import InstantMessage

from libs.common import ReceiptCommand
from libs.common import Log
from libs.server import Session, Server
from libs.client import Dialog

from .cmd import CPU
from .config import g_facebook, g_database, g_session_server, g_receptionist, g_monitor
from .config import station_name, chat_bot


class MessageProcessor:

    def __init__(self, request_handler):
        super().__init__()
        self.__handler = request_handler
        self.__dialog: Dialog = None
        self.__cpu = CPU(facebook=g_facebook, database=g_database, session_server=g_session_server)

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    @property
    def client_address(self) -> str:
        return self.__handler.client_address

    @property
    def identifier(self) -> ID:
        return self.__handler.identifier

    @property
    def station(self) -> Server:
        return self.__handler.station

    def current_session(self, identifier: ID=None) -> Session:
        return self.__handler.current_session(identifier=identifier)

    def check_session(self, identifier: ID) -> Content:
        return self.__handler.check_session(identifier=identifier)

    """
        main entrance
    """
    def process(self, msg: InstantMessage) -> Content:
        # try to decrypt message
        sender = g_facebook.identifier(msg.envelope.sender)
        content = msg.content
        if isinstance(content, HistoryCommand):
            pass
        elif isinstance(content, Command):
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            self.info('command from client %s, %s' % (self.client_address, content))
            return self.process_command(cmd=Command(content), sender=sender)
        else:
            # talk with station?
            self.info('message from client %s, %s' % (self.client_address, content))
            return self.process_dialog(content=content, sender=sender)

    def process_dialog(self, content: Content, sender: ID) -> Content:
        if self.__dialog is None:
            self.__dialog = Dialog()
            self.__dialog.bots = [chat_bot('tuling'), chat_bot('xiaoi')]
        self.info('@@@ call NLP and response to the client %s, %s' % (self.client_address, sender))
        nickname = g_facebook.nickname(identifier=sender)
        response = self.__dialog.query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            assert isinstance(content, TextContent)
            question = content.text
            answer = response.text
            self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            return response
        # TEST: response client with the same message here
        Log.info('Dialog > message from %s(%s): %s' % (nickname, sender, content))
        return content

    def process_command(self, cmd: Command, sender: ID) -> Content:
        command = cmd.command
        if 'handshake' == command:
            # handshake protocol
            return self.process_handshake(sender=sender, cmd=HandshakeCommand(cmd))
        if 'meta' == command:
            # meta protocol
            return self.process_meta_command(cmd=MetaCommand(cmd))
        if 'profile' == command:
            # profile protocol
            return self.process_profile_command(cmd=ProfileCommand(cmd))
        # check session valid
        handshake = self.check_session(identifier=sender)
        if handshake is not None:
            return handshake
        if 'broadcast' == command or 'report' == command:
            # broadcast or report
            return self.process_broadcast_command(cmd=cmd)
        # extra commands will be processed by Command Process Units
        self.info('extra command: %s, sender: %s' % (cmd, sender))
        return self.__cpu.process(cmd=cmd, sender=sender)

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
        identifier = g_facebook.identifier(cmd.identifier)
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
        identifier = g_facebook.identifier(cmd.identifier)
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
