# -*- coding: utf-8 -*-

"""
    Android Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""

import jpush

from dimp import ID

from dimples.server import PushService, PushInfo

from ..utils import Logging


class AndroidPushNotificationService(PushService, Logging):

    # TODO: read values from 'config.ini'
    app_key = "db6d7573a1643e36cf2451c6"
    master_secret = "d6ddc704ce0cde1d7462b4f4"
    apns_production = False

    def push(self, alias: str, message: str) -> bool:

        _jpush = jpush.JPush(self.app_key, self.master_secret)
        push = _jpush.create_push()
        # if you set the logging level to "DEBUG",it will show the debug logging.
        _jpush.set_logging("DEBUG")

        option = {"apns_production": self.apns_production}

        push.audience = jpush.audience(jpush.alias(alias))
        push.notification = jpush.notification(alert=message)
        push.platform = jpush.all_
        push.options = option

        try:
            response = push.send()
            self.info(msg='push response: %s' % response)
            return True
        except jpush.common.Unauthorized:
            raise jpush.common.Unauthorized("Unauthorized")
        except jpush.common.APIConnectionException:
            raise jpush.common.APIConnectionException("conn error")
        except jpush.common.JPushFailure:
            print("JPushFailure")
        except Exception as e:
            print("Exception: %s" % e)

    #
    #   PushService
    #

    # Override
    def push_notification(self, sender: ID, receiver: ID, info: PushInfo = None,
                          title: str = None, content: str = None, image: str = None,
                          badge: int = 0, sound: str = None):
        # TODO: check whether receiver has signed-in via Android client
        return self.push(alias=str(receiver.address), message=content)
