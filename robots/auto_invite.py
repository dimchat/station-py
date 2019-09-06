#! /usr/bin/env python

import json
import sys, os
from cmd import Cmd
from time import sleep
import socket
from threading import Thread
from dimp import GroupCommand, InstantMessage, ReliableMessage, Transceiver

from secret import assistant_id, assistant_pk, assistant_sk, assistant_meta, assistant_profile

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from dkd import Envelope

from dimp import ID, Profile
from dimp import ContentType, Content, Command, TextContent
from dimp import InstantMessage, ReliableMessage
from dimp import HandshakeCommand, MetaCommand, ProfileCommand

from common import base64_encode, Log
from common import g_facebook, g_keystore, g_messenger, g_database, load_accounts
from common import s001, s001_port

from robot import Robot

class Client(Robot):

    def execute(self, cmd: Command, sender: ID) -> bool:
        if super().execute(cmd=cmd, sender=sender):
            return True
        command = cmd.command
        if 'search' == command:
            self.info('##### received search response')
            if 'users' in cmd:
                users = cmd['users']
                print('      users:', json.dumps(users))
            if 'results' in cmd:
                results = cmd['results']
                print('      results:', results)
        elif 'users' == command:
            self.info('##### online users: %s' % cmd.get('message'))
            if 'users' in cmd:
                users = cmd['users']
                print('      users:', json.dumps(users))
        else:
            self.info('***** command from "%s": %s (%s)' % (sender.name, cmd['command'], cmd))

    def receive_message(self, msg: InstantMessage) -> bool:
        if super().receive_message(msg=msg):
            return True
        sender = g_facebook.identifier(msg.envelope.sender)
        content: Content = msg.content
        if content.type == ContentType.Text:
            self.info('***** Message from "%s": %s' % (sender.name, content['text']))
        else:
            self.info('!!!!! Message from "%s": %s' % (sender.name, content))



if __name__ == '__main__':
    print('auto invite is running...')

    station = s001

    robots_path = os.path.abspath( os.path.join( os.path.dirname(__file__), "." ) )

    file_to_handle = os.path.join( robots_path, 'freshmen.txt' )


    g_facebook.save_meta(identifier=assistant_id, meta=assistant_meta)
    g_facebook.save_private_key(identifier=assistant_id, private_key=assistant_sk)
    g_facebook.save_profile(profile=assistant_profile)
    # sender = LocalUserDB(assistant_id)

    sender = g_facebook.user(identifier=assistant_id)
    
    print(sender)
    g_keystore.user = sender

    gid = 'Group-Naruto@7ThVZeDuQAdG3eSDF6NeFjMDPjKN5SbrnM'

    client = Client(identifier=sender.identifier)
    client.delegate = g_facebook
    client.messenger = g_messenger
    s001.host = '134.175.87.98'
    s001.port = 9394
    client.connect(station=s001)
    group = client.delegate.group(ID(gid))

    sleep(5)
    cmd = GroupCommand.query( group.identifier)
    receiver = g_facebook.identifier('baloo@4LA5FNbpxP38UresZVpfWroC2GVomDDZ7q')
    client.check_meta(identifier=receiver)
    client.send_content(content=cmd, receiver=receiver)
    print(group.identifier)

    # client.disconnect()
    # client = None

    while False:
        with open( file_to_handle,'r') as f:
            lines = f.readlines()
            for l in lines:
                cmd = GroupCommand.invite(group=gid, member=l)

                i_msg = InstantMessage.new(content=cmd, sender=sender.identifier, receiver=gid)
                
                r_msg = g_messenger.encrypt_sign(i_msg)
                
                print(cmd)
                print(l)
        sleep(10)

