# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""

from typing import Optional

from dimples import ID
from dimples.server import ServerSession as SuperSession

from ..database import Database

from .monitor import Monitor


class ServerSession(SuperSession):
    """
        Session for Connection
        ~~~~~~~~~~~~~~~~~~~~~~

        'key' - Session Key
                A random string generated when session initialized.
                It's used in handshaking for authentication.

        'ID' - Remote User ID
                It will be set after handshake accepted.
                So we can trust all messages from this sender after that.

        'active' - Session Status
                It will be set to True after connection build.
                After received 'offline' command, it will be set to False;
                and when received 'online' it will be True again.
                Only push message when it's True.
    """

    # Override
    def set_identifier(self, identifier: ID) -> bool:
        old = self.identifier
        if super().set_identifier(identifier=identifier):
            session_change_id(session=self, new_id=identifier, old_id=old)
            return True

    # Override
    def set_active(self, active: bool, when: float = None):
        if super().set_active(active=active, when=when):
            session_change_active(session=self, active=active)
        # check for login
        identifier = self.identifier
        if identifier is not None:
            remote_address = self.remote_address
            monitor = Monitor()
            if active:
                monitor.user_online(sender=identifier, when=when, remote_address=remote_address)
            else:
                monitor.user_offline(sender=identifier, when=when, remote_address=remote_address)


def session_change_id(session: ServerSession, new_id: ID, old_id: Optional[ID]):
    remote = session.remote_address
    db = session.database
    assert isinstance(db, Database), 'database error: %s' % db
    if old_id is not None:
        # remove socket address for old user
        db.remove_socket_address(identifier=old_id, address=remote)
    if new_id is not None:  # and session.active:
        # store socket address for new user
        return db.add_socket_address(identifier=new_id, address=remote)


def session_change_active(session: ServerSession, active: bool):
    identifier = session.identifier
    if identifier is None:
        # user not login yet
        return False
    remote = session.remote_address
    db = session.database
    assert isinstance(db, Database), 'database error: %s' % db
    if active:
        # store socket address for this user
        return db.add_socket_address(identifier=identifier, address=remote)
    else:
        # remove socket address for this user
        return db.remove_socket_address(identifier=identifier, address=remote)
