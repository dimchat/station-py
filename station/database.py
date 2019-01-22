# -*- coding: utf-8 -*-

import os
import time

import dimp


class Database:

    def store_message(self, msg: dimp.ReliableMessage) -> bool:
        receiver = msg.envelope.receiver
        directory = '/tmp/dim/accounts/' + receiver.address + '/messages'
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        path = directory + '/' + filename + '.msg'
        with open(path, 'w') as file:
            file.write('%s\n' % msg)
        print('msg write into file: ', path)
        return True


database = Database()
