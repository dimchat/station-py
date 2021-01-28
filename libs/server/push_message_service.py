import traceback
import pika
import json
from dimp import ID

from libs.utils import Singleton


@Singleton
class PushMessageService:

    queue_key = "dim_push_message"

    def push(self, sender: ID, receiver: ID, message: str):
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

        except Exception as error:
            print('Push exception: %s' % error)

            exception_str = traceback.format_exc()
            print("Push exception happen {}".format(exception_str))

#
# if __name__ == "__main__":
#
#     pusher = PushMessageService()
#     pusher.push("pony@4TnzoxrZSPVwFg7hmK7W12Wh1iu3hGz5G5", "dim@4MVvC3bTTYqozq4XvXVMt5VSWLyLK1XSVg", "Hello")
