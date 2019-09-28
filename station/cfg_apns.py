# -*- coding: utf-8 -*-

"""
    Apple Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Paths for APNs credentials
"""

import os

path = os.path.abspath(os.path.dirname(__file__))
root = os.path.split(path)[0]
etc = os.path.join(root, 'etc')

apns_credentials = os.path.join(etc, 'apns', 'credentials.pem')
