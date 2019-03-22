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
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""

from json import JSONDecodeError
from threading import Thread
from time import sleep

import dimp

from .database import Database
from .session import SessionServer


class Receptionist(Thread):

    def __init__(self):
        super().__init__()
        self.guests = []
        self.database: Database = None
        self.session_server: SessionServer = None
        self.station = None

    def add_guest(self, identifier: dimp.ID):
        self.guests.append(identifier)

    def request_handler(self, identifier: dimp.ID):
        return self.session_server.request_handler(identifier=identifier)

    def run(self):
        print('starting receptionist...')
        while self.station.running:
            try:
                guests = self.guests.copy()
                for identifier in guests:
                    print('receptionist: checking session for new guest %s' % identifier)
                    handler = self.request_handler(identifier=identifier)
                    if handler:
                        print('receptionist: %s is connected, scanning messages for it' % identifier)
                        # this guest is connected, scan messages for it
                        messages = self.database.load_messages(identifier)
                        if messages:
                            print('receptionist: got %d message(s) for %s' % (len(messages), identifier))
                            for msg in messages:
                                handler.push_message(msg)
                        else:
                            print('receptionist: no message for this guest, remove it: %s' % identifier)
                            self.guests.remove(identifier)
                    else:
                        print('receptionist: guest not connect, remove it: %s' % identifier);
                        self.guests.remove(identifier)
            except IOError as error:
                print('receptionist IO error:', error)
            except JSONDecodeError as error:
                print('receptionist decode error:', error)
            except TypeError as error:
                print('receptionist type error:', error)
            except ValueError as error:
                print('receptionist value error:', error)
            finally:
                # sleep 1 second for next loop
                sleep(1.0)
        print('receptionist exit!')
