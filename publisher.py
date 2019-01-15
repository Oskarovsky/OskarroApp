import pika
import traceback

class Publisher:
    def __init__(self, host, exchange, routing):
        self.host = host
        self.exchange = exchange
        self.routing = routing

    def publish(self, message):
        connection = None
        try:
            connection = self._create_connection()
            channel = connection.channel()

            channel.exchange_declare(exchange=self.exchange,
                                     exchange_type="direct")
            channel.basic_publish(exchange=self.exchange,
                                  routing_key=self.routing,
                                  body=message)

            print(" [x] Sent message %r" % message)
        except Exception as e:
            print(repr(e))
            traceback.print_exc()
            raise e
        finally:
            if connection:
                connection.close()

    def _create_connection(self):
        return pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
