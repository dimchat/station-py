# -*- coding: utf-8 -*-

from socketserver import BaseRequestHandler

from dkd.transform import json_dict, json_str
import dimp

from dimp.commands import handshake_again_command, handshake_success_command

from station.config import station, session_server, database


class DIMRequestHandler(BaseRequestHandler):

    def setup(self):
        print(station, 'set up with', self.client_address)

    def receive(self) -> list:
        data = b''
        while True:
            part = self.request.recv(1024)
            data += part
            if len(part) < 1024:
                break
        # split message(s)
        messages = []
        if len(data) > 0:
            array = data.decode('utf-8').splitlines()
            for line in array:
                msg = json_dict(line)
                msg = dimp.ReliableMessage(msg)
                messages.append(msg)
        return messages

    def handle(self):
        print('client (%s:%s) connected!' % self.client_address)

        while True:
            messages = self.receive()
            if len(messages) == 0:
                print('client (%s:%s) exit!' % self.client_address)
                break
            for r_msg in messages:
                sender = r_msg.envelope.sender
                receiver = r_msg.envelope.receiver
                # check session
                if receiver == station.identifier:
                    # process message
                    print('*** message from client (%s:%s)...' % self.client_address)
                    content = station.unpack(msg=r_msg)
                    print('    content: %s', content)
                    response = self.process(sender=sender, content=content)
                elif not session_server.valid(sender, self.client_address):
                    # handshake
                    print('*** handshake with client (%s:%s)...' % self.client_address)
                    response = self.handshake(sender=sender)
                else:
                    # save message for other users
                    print('@@@ message from "%s" to "%s"...' % (sender, receiver))
                    response = self.save(msg=r_msg)
                # pack and response
                if response:
                    print('*** response to client (%s:%s)...' % self.client_address)
                    print('    content: %s', response)
                    msg = station.pack(receiver=sender, content=response)
                    self.request.sendall(json_str(msg).encode('utf-8'))

    def process(self, sender: dimp.ID, content: dimp.Content) -> dimp.Content:
        if content.type == dimp.MessageType.Command:
            if content['command'] == 'handshake':
                return self.handshake(sender=sender, content=content)
            else:
                print('Unknown command: ', content)
        else:
            # response client with the same message
            return content

    def handshake(self, sender: dimp.ID, content: dimp.Content=None) -> dimp.Content:
        if content and 'session' in content:
            session = content['session']
        else:
            session = None
        current = session_server.session(identifier=sender)
        if session == current.session_key:
            # session verified
            current.client_address = self.client_address
            return handshake_success_command()
        else:
            return handshake_again_command(session=current.session_key)

    def save(self, msg: dimp.ReliableMessage) -> dimp.Content:
        print('message to: ', msg.envelope.receiver)
        database.store_message(msg=msg)
        content = dimp.CommandContent.new(command='response')
        content['message'] = 'Sent OK!'
        return content

    def finish(self):
        print(station, 'finish')
