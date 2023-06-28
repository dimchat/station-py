# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import time
from typing import Optional, Tuple, List

from dimples import ID, ContentType, Envelope, ReliableMessage
from dimples.server import PushService, BadgeKeeper
from dimples.server import AnsCommandProcessor, FilterManager

from ..utils import Logging
from ..common import CommonFacebook
from ..common import PushCommand, PushItem

from .emitter import Emitter


class DefaultPushService(PushService, Logging):

    MESSAGE_EXPIRES = 128

    def __init__(self, badge_keeper: BadgeKeeper, facebook: CommonFacebook, emitter: Emitter):
        super().__init__()
        self.__keeper = badge_keeper
        self.__facebook = facebook
        self.__emitter = emitter
        self.__bot = None

    @property
    def bot(self) -> Optional[ID]:
        receiver = self.__bot
        if receiver is None:
            receiver = AnsCommandProcessor.ans_id(name='apns')
            self.__bot = receiver
        return receiver

    # Override
    def process(self, messages: List[ReliableMessage]) -> bool:
        try:
            bot = self.bot
            if bot is None:
                self.warning(msg='apns bot not set')
                return False
            mute_filter = FilterManager().mute_filter
            expired = time.time() - self.MESSAGE_EXPIRES
            items = []
            for msg in messages:
                if msg.time < expired:
                    env = self._origin_envelope(msg=msg)
                    self.warning(msg='drop expired message: %s -> %s (group: %s) type: %d'
                                     % (env.sender, msg.receiver, env.group, env.type))
                    continue
                if mute_filter.is_muted(msg=msg):
                    env = self._origin_envelope(msg=msg)
                    self.info(msg='muted sender: %s -> %s (group: %s) type: %d'
                                  % (env.sender, msg.receiver, env.group, env.type))
                    continue
                # build push item for message
                pi = self.__build_push_item(msg=msg)
                if pi is not None:
                    items.append(pi)
            if len(items) > 0:
                # push items to the bot
                bot = self.bot
                if bot is not None:
                    content = PushCommand(items=items)
                    emitter = self.__emitter
                    emitter.send_content(content=content, receiver=bot)
        except Exception as error:
            self.error(msg='push %d messages error: %s' % (len(messages), error))
        return True

    def __build_push_item(self, msg: ReliableMessage) -> Optional[PushItem]:
        # 1. check original sender, group & msg type
        env = self._origin_envelope(msg=msg)
        receiver = msg.receiver
        sender = env.sender
        group = env.group
        msg_type = env.type
        # 2. build title & content text
        title, text = self._build_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type)
        if text is None:
            self.info(msg='ignore msg type: %s -> %s (group: %s) type: %d' % (sender, receiver, group, msg_type))
            return None
        # 3. increase badge
        keeper = self.__keeper
        badge = keeper.increase_badge(identifier=receiver)
        return PushItem.create(receiver=receiver, title=title, content=text, badge=badge)

    # noinspection PyMethodMayBeStatic
    def _origin_envelope(self, msg: ReliableMessage) -> Envelope:
        """ get envelope of original message """
        origin = msg.get('origin')
        if origin is None:
            env = msg.envelope
        else:
            # forwarded message, separated by group assistant?
            env = Envelope.parse(envelope=origin)
            msg.pop('origin', None)
        return env

    def _build_message(self, sender: ID, receiver: ID, group: ID, msg_type: int) -> Tuple[Optional[str], Optional[str]]:
        """ build title, content for notification """
        facebook = self.__facebook
        return build_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type, facebook=facebook)


def build_message(sender: ID, receiver: ID, group: ID, msg_type: int,
                  facebook: CommonFacebook) -> Tuple[Optional[str], Optional[str]]:
    """ PNs: build text message for msg """
    if msg_type == 0:
        title = 'Message'
        something = 'a message'
    elif msg_type == ContentType.TEXT:
        title = 'Text Message'
        something = 'a text message'
    elif msg_type == ContentType.FILE:
        title = 'File'
        something = 'a file'
    elif msg_type == ContentType.IMAGE:
        title = 'Image'
        something = 'an image'
    elif msg_type == ContentType.AUDIO:
        title = 'Voice'
        something = 'a voice message'
    elif msg_type == ContentType.VIDEO:
        title = 'Video'
        something = 'a video'
    elif msg_type in [ContentType.MONEY, ContentType.TRANSFER]:
        title = 'Money'
        something = 'some money'
    else:
        # unknown type
        return None, None
    from_name = get_name(identifier=sender, facebook=facebook)
    to_name = get_name(identifier=receiver, facebook=facebook)
    text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
    if group is not None:
        text += ' in group [%s]' % get_name(identifier=group, facebook=facebook)
    return title, text


def get_name(identifier: ID, facebook: CommonFacebook) -> str:
    doc = facebook.document(identifier=identifier)
    if doc is not None:
        name = doc.name
        if name is not None and len(name) > 0:
            return name
    name = identifier.name
    if name is not None and len(name) > 0:
        return name
    return str(identifier.address)
