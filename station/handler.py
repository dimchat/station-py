# -*- coding: utf-8 -*-

from socketserver import BaseRequestHandler

from dkd.transform import json_dict, json_str
import dimp

from dimp.commands import handshake_again_command, handshake_success_command

from station.config import station
from station.transceiver import transceiver
from station.session import Session
from station.database import database


class DIMRequestHandler(BaseRequestHandler):

    def setup(self):
        print(station, 'set up')

    def receive(self):
        data = b''
        while True:
            part = self.request.recv(1024)
            data += part
            if len(part) < 1024:
                break
        return data

    def handle(self):
        address, pid = self.client_address
        print('%s(pid: %s) connected!' % (address, pid))

        while True:
            data = self.receive()
            if len(data) == 0:
                print('%s(pid: %s) closed!' % (address, pid))
                break
            data = json_dict(data)
            r_msg = dimp.ReliableMessage(data)
            # process message
            if r_msg.envelope.receiver == station.identifier:
                response = self.process(msg=r_msg)
            else:
                # save message for other users
                response = self.save(msg=r_msg)
            if response:
                response = json_str(response)
                self.request.sendall(response.encode('utf-8'))
                print('response to %s(pid: %s): %s' % (address, pid, response))

    def process(self, msg: dimp.ReliableMessage) -> dimp.ReliableMessage:
        sender = msg.envelope.sender
        msg = transceiver.verify(msg)
        msg = transceiver.decrypt(msg)
        content = msg.content
        print('received message content: ', content)
        response = None
        if content.type == dimp.MessageType.Command:
            if content['command'] == 'handshake':
                if 'session' in content:
                    session = content['session']
                else:
                    session = None
                current = Session.session(identifier=sender)
                if session == current.session_key:
                    response = handshake_success_command()
                else:
                    response = handshake_again_command(session=current.session_key)
        else:
            response = content
        # packing response
        if response:
            env = dimp.Envelope(sender=station.identifier, receiver=sender)
            msg = dimp.InstantMessage.new(content=response, envelope=env)
            msg = transceiver.encrypt(msg)
            msg = transceiver.sign(msg)
            return msg
        else:
            print('Unknown request:', content)
            return None

    def save(self, msg: dimp.ReliableMessage) -> dimp.ReliableMessage:
        print('message to: ', msg.envelope.receiver)
        database.store_message(msg=msg)
        content = dimp.CommandContent.new(command='response')
        content['message'] = 'Sent OK!'
        env = dimp.Envelope(sender=station.identifier, receiver=msg.envelope.sender)
        msg = dimp.InstantMessage.new(content=content, envelope=env)
        msg = transceiver.encrypt(msg=msg)
        msg = transceiver.sign(msg=msg)
        return msg

    def finish(self):
        print(station, 'finish')
