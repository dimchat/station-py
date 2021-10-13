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

from libs.utils import Logging
from libs.utils import NotificationCenter
from libs.common import NotificationNames
from libs.common import CompletionHandler, MessengerDelegate
from libs.server import ServerMessenger, SessionServer


class RequestHandler(StreamRequestHandler, MessengerDelegate, Logging):

    def __init__(self, request, client_address, server):
        # messenger
        mess = ServerMessenger()
        mess.delegate = self
        # session
        sess = SessionServer().get_session(client_address=client_address, messenger=mess, sock=request)
        mess.current_session = sess
        self.__messenger = mess
        # init
        super().__init__(request=request, client_address=client_address, server=server)

    @property
    def messenger(self) -> ServerMessenger:
        return self.__messenger

    #
    #
    #
    def setup(self):
        super().setup()
        try:
            session = self.messenger.current_session
            self.info('client connected: %s' % session)
            session.setup()
            NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
                'session': session,
            })
        except Exception as error:
            self.error('setup request handler error: %s' % error)
            traceback.print_exc()

    def finish(self):
        try:
            session = self.messenger.current_session
            self.info('client disconnected: %s' % session)
            SessionServer().remove_session(session=session)
            NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
                'session': session,
            })
            session.finish()
            self.messenger.current_session = None
        except Exception as error:
            self.error('finish request handler error: %s' % error)
            traceback.print_exc()
        super().finish()

    """
        DIM Request Handler
    """

    def handle(self):
        super().handle()
        try:
            self.info('session started: %s' % str(self.client_address))
            session = self.messenger.current_session
            session.handle()
            self.info('session finished: %s' % str(self.client_address))
        except Exception as error:
            self.error('request handler error: %s' % error)
            traceback.print_exc()

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler, priority: int = 0) -> bool:
        session = self.messenger.current_session
        if session is not None and session.send_payload(payload=data, priority=priority):
            if handler is not None:
                handler.success()
            return True
        else:
            if handler is not None:
                error = IOError('MessengerDelegate error: failed to send data package')
                handler.failed(error=error)
            return False

    def upload_data(self, data: bytes, msg: InstantMessage) -> Optional[str]:
        # upload encrypted file data
        self.info('upload %d bytes for: %s' % (len(data), msg.content))
        return None

    def download_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        # download encrypted file data
        self.info('download %s for: %s' % (url, msg.content))
        return None
