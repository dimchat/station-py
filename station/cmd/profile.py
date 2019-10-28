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
    Command Processor for 'profile'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    profile protocol
"""

from dimp import ID, Profile
from dimp import Content, TextContent
from dimp import Command, ProfileCommand

from libs.common import ReceiptCommand

from .cpu import CPU


class ProfileCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        assert isinstance(cmd, ProfileCommand)
        identifier = self.facebook.identifier(cmd.identifier)
        meta = cmd.meta
        if meta is not None:
            # received a meta for ID
            if self.facebook.save_meta(identifier=identifier, meta=meta):
                self.info('meta saved %s, %s' % (identifier, meta))
            else:
                self.error('meta not match %s, %s' % (identifier, meta))
                return TextContent.new(text='Meta not match %s!' % identifier)
        profile = cmd.profile
        if profile is not None:
            # received a new profile for ID
            self.info('received profile %s' % identifier)
            if self.facebook.save_profile(profile=profile):
                self.info('profile saved %s' % profile)
                return ReceiptCommand.new(message='Profile of %s received!' % identifier)
            else:
                self.error('profile not valid %s' % profile)
                return TextContent.new(text='Profile signature not match %s!' % identifier)
        # querying profile for ID
        self.info('search profile %s' % identifier)
        profile = self.facebook.profile(identifier=identifier)
        if identifier == self.request_handler.station.identifier:
            # querying profile of current station
            private_key = self.facebook.private_key_for_signature(identifier=identifier)
            if private_key is not None:
                if profile is None:
                    profile = Profile.new(identifier=identifier)
                # NOTICE: maybe the station manager config different station with same ID,
                #         or the client query different station with same ID,
                #         so we need to correct station name here
                profile.name = self.station_name
                profile.sign(private_key=private_key)
        # response
        if profile is not None:
            return ProfileCommand.response(identifier=identifier, profile=profile)
        else:
            return TextContent.new(text='Sorry, profile for %s not found.' % identifier)
