#! /usr/bin/env python3
# -*- coding: utf-8 -*-
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
    Station bot: 'Push Center'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Bot as Push Center
"""
import time
from typing import Optional, Union, List

from dimples import ContentType, Content, ReliableMessage
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseCommandProcessor
from dimples.client import ClientContentProcessorCreator
from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Logging
from libs.common import PushCommand
from libs.client import ClientProcessor
from libs.push import PushNotificationClient
from libs.push import ApplePushNotificationService
from libs.push import AndroidPushNotificationService

from sbots.shared import GlobalVariable
from sbots.shared import start_bot


class PushCommandProcessor(BaseCommandProcessor, Logging):

    MESSAGE_EXPIRES = 256

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, PushCommand), 'push command error: %s' % content
        items = content.items
        # check expired
        expired = time.time() - self.MESSAGE_EXPIRES
        if msg.time < expired:
            self.warning(msg='drop expired push items: %s' % items)
            return []
        else:
            self.info(msg='push %d item(s).' % len(items))
        # add push task
        pnc = PushNotificationClient()
        pnc.add_task(items=items, msg_time=msg.time)
        return []


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # push
        if cmd == PushCommand.PUSH:
            return PushCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


def create_apns(shared: GlobalVariable):
    pnc = PushNotificationClient()
    pnc.delegate = shared.database
    config = shared.config
    # 1. add push service: APNs
    credentials = config.get_string(section='push', option='apns_credentials')
    use_sandbox = config.get_boolean(section='push', option='apns_use_sandbox')
    topic = config.get_string(section='push', option='apns_topic')
    print('APNs: credentials=%s, use_sandbox=%s, topic=%s' % (credentials, use_sandbox, topic))
    if credentials is not None and len(credentials) > 0:
        apple = ApplePushNotificationService(credentials=credentials,
                                             use_sandbox=use_sandbox)
        if topic is not None and len(topic) > 0:
            apple.topic = topic
        pnc.apple_pns = apple
    # 2. add push service: JPush
    app_key = config.get_string(section='push', option='app_key')
    master_secret = config.get_string(section='push', option='master_secret')
    production = config.get_boolean(section='push', option='apns_production')
    print('APNs: app_key=%s, master_secret=%s, production=%s' % (app_key, master_secret, production))
    if app_key is not None and len(app_key) > 0 and master_secret is not None and len(master_secret) > 0:
        android = AndroidPushNotificationService(app_key=app_key,
                                                 master_secret=master_secret,
                                                 apns_production=production)
        pnc.android_pns = android


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


if __name__ == '__main__':
    start_bot(default_config=DEFAULT_CONFIG,
              app_name='DIM Push Center',
              ans_name='apns',
              processor_class=BotMessageProcessor)
    # create push services
    create_apns(shared=GlobalVariable())
