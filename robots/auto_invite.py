#! /usr/bin/env python

import sys, os
from time import sleep
from dimp import GroupCommand, InstantMessage, ReliableMessage, Transceiver

from secret import assistant_id, assistant_pk, assistant_sk, assistant_meta, assistant_profile

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from dimp import ID, Profile
from dimp import ContentType, Content, Command, TextContent
from dimp import InstantMessage, ReliableMessage
from dimp import HandshakeCommand, MetaCommand, ProfileCommand

from common import base64_encode, Log
from common import g_facebook, g_keystore, g_messenger, g_database, load_accounts

robots_path = os.path.abspath( os.path.join( os.path.dirname(__file__), "." ) )

file_to_handle = os.path.join( robots_path, 'freshmen.txt' )

if __name__ == '__main__':
    print('auto invite is running...')

    g_facebook.save_meta(identifier=assistant_id, meta=assistant_meta)
    g_facebook.save_private_key(identifier=assistant_id, private_key=assistant_sk)
    g_facebook.save_profile(profile=assistant_profile)
    # sender = LocalUserDB(assistant_id)

    sender = g_facebook.user(identifier=assistant_id)
    
    print(sender)
    g_keystore.user = sender

    gid = 'Group-Naruto@7ThVZeDuQAdG3eSDF6NeFjMDPjKN5SbrnM'

    while True:
        with open( file_to_handle,'r') as f:
            lines = f.readlines()
            for l in lines:
                cmd = GroupCommand.invite(group=gid, member=l)

                i_msg = InstantMessage.new(content=cmd, sender=sender.identifier, receiver=l)
                
                r_msg = g_messenger.encrypt_sign(i_msg)
                
                print(cmd)
                print(l)
        sleep(10)
