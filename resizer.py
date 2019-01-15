import pika
import time
from wand.image import Image
import jwt
from pathlib import Path

queue="q1"
exchange="slyko-exchange"
routing_key="resize"
jwt_secret_key = 'DjOskarroInDaMix'

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue=queue, durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')

channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)
    try:
        msg = jwt.decode(body, jwt_secret_key, algorithm='HS256')
        print(msg)
        openpath = Path(msg['openpath'])
        savepath = Path(msg['savepath'])
        with Image(filename=str(openpath)) as img:
            print(img.size)
            i = img.clone()
            i.resize(64, 64)
            savepath.mkdir(parents=True, exist_ok=True)
            i.save(filename=str(savepath.joinpath(openpath.name)))

    except jwt.ExpiredSignatureError:
        print("Invalid jwt signature")
    print(" [x] Done")
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback, queue=queue)

channel.start_consuming()