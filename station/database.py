# -*- coding: utf-8 -*-

import os
import time

import dimp


def store_message(msg: dimp.ReliableMessage) -> bool:
    receiver = msg.envelope.receiver
    directory = 'users/' + receiver.address + '/messages'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    path = directory + '/' + filename + '.msg'
    with open(path, 'w') as file:
        file.write('%s\n' % msg)
    print('msg write into file: ', path)
    return True
