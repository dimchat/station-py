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
    Request Handler
    ~~~~~~~~~~~~~~~

    Handler for each connection
"""

import traceback
from socketserver import StreamRequestHandler
from typing import Optional

from dimp import InstantMessage

from libs.utils.log import Logging
from libs.common import MessengerDelegate
from libs.server import Session, SessionServer
from libs.server import ServerMessenger


class RequestHandler(StreamRequestHandler, MessengerDelegate, Logging):

    def __init__(self, request, client_address, server):
        # messenger
        messenger = ServerMessenger()
        messenger.delegate = self
        self.__messenger = messenger
        # init
        super().__init__(request=request, client_address=client_address, server=server)

    @property
    def messenger(self) -> ServerMessenger:
        return self.__messenger

    # Override
    def setup(self):
        super().setup()
        try:
            messenger = self.messenger
            session = Session(messenger=messenger, address=self.client_address, sock=self.request)
            messenger.session = session
            SessionServer().add_session(session=session)
            self.info('client connected: %s' % session)
            session.setup()
        except Exception as error:
            self.error('setup request handler error: %s' % error)
            traceback.print_exc()

    # Override
    def finish(self):
        try:
            session = self.messenger.session
            self.info('client disconnected: %s' % session)
            SessionServer().remove_session(session=session)
            session.finish()
            self.messenger.session = None
        except Exception as error:
            self.error('finish request handler error: %s' % error)
            traceback.print_exc()
        super().finish()

    """
        DIM Request Handler
    """

    # Override
    def handle(self):
        super().handle()
        try:
            self.info('session started: %s' % str(self.client_address))
            session = self.messenger.session
            session.handle()
            self.info('session finished: %s' % str(self.client_address))
        except Exception as error:
            self.error('request handler error: %s' % error)
            traceback.print_exc()

    #
    #   MessengerDelegate
    #

    # Override
    def upload_encrypted_data(self, data: bytes, msg: InstantMessage) -> Optional[str]:
        # upload encrypted file data
        self.info('upload %d bytes for: %s' % (len(data), msg.content))
        return None

    # Override
    def download_encrypted_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        # download encrypted file data
        self.info('download %s for: %s' % (url, msg.content))
        return None
