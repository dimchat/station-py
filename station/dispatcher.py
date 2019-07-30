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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

from dimp import ID
from dimp import ReliableMessage

from common import database, facebook, Log

from .session import session_server
from .apns import apns


class Dispatcher:

    def __init__(self):
        super().__init__()

    def deliver(self, msg: ReliableMessage) -> bool:
        receiver = msg.envelope.receiver
        receiver = ID(receiver)
        # try for online user
        sessions = session_server.search(identifier=receiver)
        if sessions and len(sessions) > 0:
            Log.info('Dispatcher: %s is online(%d), try to push message: %s' % (receiver, len(sessions), msg.envelope))
            success = 0
            for sess in sessions:
                if sess.valid is False or sess.active is False:
                    Log.info('Dispatcher: session invalid %s' % sess)
                    continue
                if sess.request_handler.push_message(msg):
                    success = success + 1
                else:
                    Log.info('Dispatcher: failed to push message via connection (%s, %s)' % sess.client_address)
            if success > 0:
                Log.info('Dispatcher: message pushed to activated session(%d) of user: %s' % (success, receiver))
                return True
        # store in local cache file
        Log.info('Dispatcher: %s is offline, store message: %s' % (receiver, msg.envelope))
        database.store_message(msg)
        # push notification
        account = facebook.account(identifier=receiver)
        account.delegate = database
        sender = msg.envelope.sender
        sender = ID(sender)
        contact = facebook.account(identifier=sender)
        contact.delegate = database
        text = 'Dear %s: %s sent you a message.' % (account.name, contact.name)
        return apns.push(identifier=receiver, message=text)


dispatcher = Dispatcher()
dispatcher.session_server = session_server
dispatcher.barrack = facebook
dispatcher.database = database
dispatcher.apns = apns
