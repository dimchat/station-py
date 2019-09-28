# -*- coding: utf-8 -*-

"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""

import os

from common import Storage

path = os.path.abspath(os.path.dirname(__file__))
root = os.path.split(path)[0]
etc = os.path.join(root, 'etc')

# chat bot: Tuling
tuling_keys = Storage.read_json(path=os.path.join(etc, 'tuling', 'secret.js'))
tuling_ignores = [4003]

# chat bot XiaoI
xiaoi_keys = Storage.read_json(path=os.path.join(etc, 'xiaoi', 'secret.js'))
xiaoi_ignores = ['默认回复', '重复回复']
