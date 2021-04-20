# -*- coding: utf-8 -*-

"""
    Apple Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Paths for APNs credentials
"""

import os

etc = os.path.abspath(os.path.dirname(__file__))

# /srv/dims/etc/apns/credentials.pem
apns_credentials = os.path.join(etc, 'apns', 'credentials.pem')
# apns_credentials = None

apns_use_sandbox = False
apns_topic = 'chat.dim.client'
