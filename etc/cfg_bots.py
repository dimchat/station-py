# -*- coding: utf-8 -*-

"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""

import os

from dimp import ID

from libs.common import Storage

etc = os.path.abspath(os.path.dirname(__file__))

# chat bot: Tuling
tuling_keys = Storage.read_json(path=os.path.join(etc, 'tuling', 'secret.js'))
tuling_ignores = [4003]

# chat bot XiaoI
xiaoi_keys = Storage.read_json(path=os.path.join(etc, 'xiaoi', 'secret.js'))
xiaoi_ignores = ['默认回复', '重复回复']


#
#  DIM chat bots
#

lingling_id = 'lingling@2PemMVAvxpuVZw2SYwwo11iBBEBb7gCvDHa'

xiaoxiao_id = 'xiaoxiao@2PhVByg7PhEtYPNzW5ALk9ygf6wop1gTccp'


#
#  DIM system bots
#

assistant_id = 'assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq'


#
#  Shodai Hokage
#

group_naruto = 'Group-Naruto@7ThVZeDuQAdG3eSDF6NeFjMDPjKN5SbrnM'

freshmen_file = '/data/.dim/freshmen.txt'
# freshmen_file = '/tmp/freshmen.txt'  # test


#
#  Info Loader
#

def load_robot_info(identifier: ID, filename: str) -> dict:
    return Storage.read_json(path=os.path.join(etc, identifier.address, filename))


def load_freshmen() -> list:
    text = Storage.read_text(freshmen_file)
    if text is not None:
        return text.splitlines()
