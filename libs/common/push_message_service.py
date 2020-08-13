import pika
from pika import BlockingConnection
import json


class PushMessageService:

    connection: BlockingConnection
    queue_key = "dim_push_message"

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_key)

    def push(self, sender: str, receiver: str, message: str):
        try:
            json_dict = {
                "from": sender,
                "to": receiver,
                "message": "{0}".format(message),
                "platform": "ios"
            }

            json_str = json.dumps(json_dict)
            print("Now publish to rabbitmq {}".format(json_str))
            self.channel.basic_publish(exchange='', routing_key=self.queue_key, body=json_str)
        except:
            pass
