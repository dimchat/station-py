# -*- coding: utf-8 -*-

"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""

import os

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

tokentalkteam_id = 'TokenTalkTeam@2PraD3pKpPg77N4AdaeSHRy1jwYfP16vBRH'


#
#  DIM system bots
#

group_assistants = [
    'assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq',
]

#
#  DIM demo
#

chatroom_id = 'chatroom-admin@2Pc5gJrEQYoz9D9TJrL35sA3wvprNdenPi7'


#
#  Shodai Hokage
#

group_naruto = 'Group-Naruto@7ThVZeDuQAdG3eSDF6NeFjMDPjKN5SbrnM'
