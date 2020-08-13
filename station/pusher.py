import pika
from pika import BlockingConnection
import json
import jpush


class Pusher:

    connection: BlockingConnection
    queue_key = "dim_push_message"

    app_key = "db6d7573a1643e36cf2451c6"
    master_secret = "d6ddc704ce0cde1d7462b4f4"
    apns_production = False

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_key)

    def start(self):
        print(' [*] Waiting for push messages. To exit press CTRL+C')
        self.channel.basic_consume(self.queue_key, self.get_request, True)
        self.channel.start_consuming()

    def get_request(self, ch, method, properties, body):

        json_str = body.decode("utf-8")

        print("Received message {}".format(json_str))

        json_dict = json.loads(json_str)

        message = json_dict["message"]
        receiver = json_dict["to"]

        self.push(receiver, message)

    def push(self, alias: str, message: str):

        _jpush = jpush.JPush(self.app_key, self.master_secret)
        push = _jpush.create_push()
        # if you set the logging level to "DEBUG",it will show the debug logging.
        _jpush.set_logging("DEBUG")

        option = {"apns_production": self.apns_production}

        push.audience = jpush.audience(jpush.alias(alias))
        push.notification = jpush.notification(alert=message)
        push.platform = jpush.all_
        push.options = option

        try:
            response = push.send()
        except jpush.common.Unauthorized:
            raise jpush.common.Unauthorized("Unauthorized")
        except jpush.common.APIConnectionException:
            raise jpush.common.APIConnectionException("conn error")
        except jpush.common.JPushFailure:
            print("JPushFailure")
        except:
            print("Exception")


if __name__ == "__main__":

    pusher = Pusher()
    # pusher.start()
    pusher.push("dim@4Q8YfNC84nYJ9EUAUjdark2usjHfTu4gUd", "Hello DIMTalk")
