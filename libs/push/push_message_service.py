import traceback
from typing import Optional

import pika
import json

from ipx import Singleton

from dimp import ID

from .service import PushService


@Singleton
class PushMessageService(PushService):

    queue_key = "dim_push_message"

    #
    #   PushService
    #

    # Override
    def push_notification(self, sender: ID, receiver: ID, message: str, badge: Optional[int] = None) -> bool:
        try:

            connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_key)

            json_dict = {
                "from": str(sender.address),
                "to": str(receiver.address),
                "message": "{0}".format(message),
                "platform": "ios"
            }

            json_str = json.dumps(json_dict)
            print("Now publish to rabbitmq {}".format(json_str))
            channel.basic_publish(exchange='', routing_key=self.queue_key, body=json_str)
            return True
        except Exception as error:
            print('Push exception: %s' % error)

            exception_str = traceback.format_exc()
            print("Push exception happen {}".format(exception_str))


# if __name__ == "__main__":
#     pusher = PushMessageService()
#     pusher.push_notification(sender=ID.parse(identifier="pony@4TnzoxrZSPVwFg7hmK7W12Wh1iu3hGz5G5"),
#                              receiver=ID.parse(identifier="dim@4MVvC3bTTYqozq4XvXVMt5VSWLyLK1XSVg"),
#                              message="Hello")
