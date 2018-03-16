# coding:utf-8

from threading import local

from pika import ConnectionParameters, BlockingConnection, BasicProperties, PlainCredentials

from data_storage import db_settings

mq_settings = db_settings.RABBITMQ_SETTINGS["local"]
HOST = mq_settings["host"]
PORT = mq_settings["port"]
USER = mq_settings["username"]
PASSWORD = mq_settings["password"]


class RabbitmqBase(local):
    """
    消息队列基类
    """

    def __init__(self, host, port, username, password, queue, exchange, durable):
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self._queue = queue
        self._exchange = exchange
        self._durable = durable  # 是否持久化
        self._conn = None
        self.__init_connect()

    def __init_connect(self):
        credentials = PlainCredentials(self.__username, self.__password)
        params = ConnectionParameters(
            host=self.__host,
            port=self.__port,
            credentials=credentials
        )
        self._conn = BlockingConnection(params)

    def close(self):
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, msg):
        raise NotImplementedError

    def receive(self, callback=None):
        raise NotImplementedError


class RabbitmqSender(RabbitmqBase):
    """
    消息队列发送者
    """

    def __init__(self, host=HOST, port=PORT, username=USER, password=PASSWORD,
                 queue='test', exchange='', durable=False):
        super().__init__(host, port, username, password, queue, exchange, durable)
        pass

    def send(self, msg):
        channel = self._conn.channel()
        channel.queue_declare(self._queue, durable=self._durable)
        channel.exchange_declare(self._exchange, durable=self._durable)
        channel.queue_bind(self._queue, self._exchange, self._queue)
        delivery_mode = 2 if self._durable else 1
        proper = BasicProperties(delivery_mode=delivery_mode)
        channel.basic_publish(
            exchange=self._exchange,
            routing_key=self._queue,
            body=msg,
            properties=proper
        )


class RabbitmqWorker(RabbitmqBase):
    """
    消息队列接受者
    """

    def __init__(self, host=HOST, port=PORT, username=USER, password=PASSWORD,
                 queue='test', exchange='', durable=False, no_ack=False, prefetch_count=1):
        super().__init__(host, port, username, password, queue, exchange, durable)
        self._no_ack = no_ack  # 是否不发送确认
        self._prefetch_count = prefetch_count  # 同一worker分配任务数

    def receive(self, callback=None):
        if not callback:
            callback = self._callback
        channel = self._conn.channel()
        channel.exchange_declare(self._exchange, durable=self._durable)
        channel.queue_declare(self._queue, durable=self._durable)
        channel.basic_qos(prefetch_count=self._prefetch_count)
        channel.basic_consume(callback, queue=self._queue, no_ack=self._no_ack)

        # print(' [*] Waiting for messages. To exit press CTRL+C')
        channel.start_consuming()

    def _callback(self, ch, method, properties, body):
        # print(" [x] Received %r" % (body))
        if not self._no_ack:
            ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    with RabbitmqSender(queue='test1', exchange='test11') as rs:
        rs.send("mytest --> hello world")


    def my_callback(ch, method, properties, body):
        print(" [x] -----> %r" % body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        ch.close()


    with RabbitmqWorker(queue='test1', exchange='test11') as rw:
        rw.receive(callback=my_callback)
