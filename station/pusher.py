#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    DIM Notification Pusher
    ~~~~~~~~~~~~~~~~~~~~~~~

    Pushing notification for offline users
"""

import threading
import traceback
from typing import Set, Dict, List, Optional, Union

from dimp import ID

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import Log, Logging
from libs.utils.ipc import PusherPipe
from libs.utils import Runner
from libs.push import PushService, PushInfo
from libs.push import ApplePushNotificationService

from etc.config import apns_credentials, apns_use_sandbox, apns_topic
from etc.cfg_init import g_database


class Worker(Runner):
    """ Push thread """

    def __init__(self, service: PushService):
        super().__init__()
        self.__jobs: List[PushInfo] = []
        self.__lock = threading.Lock()
        self.__service = service

    def append(self, job: PushInfo):
        with self.__lock:
            self.__jobs.append(job)

    def next(self) -> Optional[PushInfo]:
        with self.__lock:
            if len(self.__jobs) > 0:
                return self.__jobs.pop(0)

    # Override
    def process(self) -> bool:
        job = self.next()
        if job is None:
            # nothing to do, return False to have a rest
            return False
        srv = self.__service
        try:
            return srv.push_notification(sender=job.sender, receiver=job.receiver, message=job.message, badge=job.badge)
        except Exception as error:
            print('[PUSH] failed to push: %s, %s' % (job, error))

    @classmethod
    def new(cls, service: PushService):
        worker = Worker(service=service)
        threading.Thread(target=worker.run, daemon=True).start()
        return worker


class Pusher(Runner, Logging):
    """ Push process """

    def __init__(self):
        super().__init__()
        self.__workers: Set[Worker] = set()
        self.__badges: Dict[ID, int] = {}
        self.__pipe = PusherPipe.secondary()

    def start(self):
        self.__pipe.start()
        self.run()

    def add_service(self, service: PushService):
        """ add push notification service """
        self.__workers.add(Worker.new(service=service))

    def __increase_badge(self, identifier: ID) -> int:
        """ get self-increasing badge """
        num = self.__badges.get(identifier, 0) + 1
        self.__badges[identifier] = num
        return num

    def __clear_badge(self, identifier: ID):
        """ clear badge for user """
        self.__badges.pop(identifier, None)

    def __process(self, info: Union[dict, str]):
        if isinstance(info, str):
            info = PushInfo.from_json(string=info)
        elif isinstance(info, dict):
            info = PushInfo.from_dict(info=info)
        else:
            raise ValueError('unknown push info: %s' % info)
        assert isinstance(info, PushInfo), 'push info error: %s' % info
        # check command
        if info.receiver == PushInfo.PUSHER_ID:
            self.info(msg='received cmd: %s' % info)
            if info.message == PushInfo.MSG_CLEAR_BADGE:
                # CMD: CLEAR BADGE.
                self.__clear_badge(identifier=info.sender)
        else:
            # check badge
            if info.badge is None:
                info.badge = self.__increase_badge(identifier=info.receiver)
            # push to all workers
            self.info(msg='%d worker(s), pushing: %s' % (len(self.__workers), info))
            for worker in self.__workers:
                worker.append(job=info)

    # Override
    def process(self) -> bool:
        info = None
        try:
            info = self.__pipe.receive()
            if info is None:
                # nothing to do now, return False to have a rest
                return False
            else:
                self.__process(info=info)
                return len(self.__workers) > 0
        except Exception as error:
            self.error('failed to process: %s, %s' % (info, error))
            traceback.print_exc()

    # Override
    def stop(self):
        self.__pipe.stop()
        for worker in self.__workers:
            worker.stop()
        super().stop()


#
#   Push process
#
g_pusher = Pusher()

#
#   APNs
#
if apns_credentials is not None:
    # APNs
    apns = ApplePushNotificationService(credentials=apns_credentials, use_sandbox=apns_use_sandbox)
    apns.topic = apns_topic
    apns.delegate = g_database
    # Pusher
    g_pusher.add_service(service=apns)


if __name__ == '__main__':
    Log.info(msg='>>> starting pusher ...')
    g_pusher.start()
    Log.info(msg='>>> pusher exits.')
