# -*- coding: utf-8 -*-

import json
import traceback

from dmtp.mtp import Departure

from dmtp import Command, HelloCommand
from dmtp import Message
from dmtp import Server as DMTPServer

from libs.common import Log

from .manager import ContactManager, FieldValueEncoder


class Server(DMTPServer):

    def __init__(self, port: int, host: str='127.0.0.1'):
        super().__init__(local_address=(host, port))
        # database for location of contacts
        db = self._create_contact_manager()
        db.identifier = 'station@anywhere'
        self.__database = db
        self.delegate = db

    def _create_contact_manager(self) -> ContactManager:
        db = ContactManager(peer=self.peer)
        db.identifier = 'station@anywhere'
        return db

    @property
    def identifier(self) -> str:
        return self.__database.identifier

    @identifier.setter
    def identifier(self, value: str):
        self.__database.identifier = value

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def process_command(self, cmd: Command, source: tuple) -> bool:
        Log.info('received cmd: %s' % cmd)
        # noinspection PyBroadException
        try:
            return super().process_command(cmd=cmd, source=source)
        except Exception:
            traceback.print_exc()
            return False

    def process_message(self, msg: Message, source: tuple) -> bool:
        Log.info('received msg from %s:\n\t%s' % (source, json.dumps(msg, cls=FieldValueEncoder)))
        # return super().process_message(msg=msg, source=source)
        return True

    def send_command(self, cmd: Command, destination: tuple) -> Departure:
        Log.info('sending cmd to %s:\n\t%s' % (destination, cmd))
        return super().send_command(cmd=cmd, destination=destination)

    def send_message(self, msg: Message, destination: tuple) -> Departure:
        Log.info('sending msg to %s:\n\t%s' % (destination, json.dumps(msg, cls=FieldValueEncoder)))
        return super().send_message(msg=msg, destination=destination)

    #
    #   Server actions
    #

    def say_hello(self, destination: tuple) -> bool:
        if super().say_hello(destination=destination):
            return True
        cmd = HelloCommand.new(identifier=self.identifier)
        self.send_command(cmd=cmd, destination=destination)
        return True
