"""Outbox-authoritative optional brokers; duplicate publication is expected."""

import json

EVENT_STREAM = "mall:events"


class OutboxBus:
    async def publish(self, envelope: dict):
        return None

    async def close(self):
        return None


class RedisStreamsBus:
    def __init__(self, connection):
        self.connection = connection

    async def publish(self, envelope: dict):
        await self.connection.client().xadd(EVENT_STREAM, {"envelope": json.dumps(envelope)})

    async def close(self):
        return None


class RabbitBus:
    def __init__(self, settings):
        self.url, self.connection = settings.rabbitmq_url, None

    async def publish(self, envelope: dict):
        import aio_pika

        if self.connection is None:
            self.connection = await aio_pika.connect_robust(self.url)
        channel = await self.connection.channel(publisher_confirms=True)
        try:
            queue = await channel.declare_queue("mall.events", durable=True)
            message = aio_pika.Message(json.dumps(envelope).encode(),
                                       delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
            await channel.default_exchange.publish(message, routing_key=queue.name)
        finally:
            await channel.close()

    async def close(self):
        if self.connection is not None:
            await self.connection.close()


class KafkaBus:
    def __init__(self, settings):
        self.servers, self.producer = settings.kafka_bootstrap_servers, None

    async def publish(self, envelope: dict):
        from aiokafka import AIOKafkaProducer

        if self.producer is None:
            self.producer = AIOKafkaProducer(bootstrap_servers=self.servers,
                                            enable_idempotence=True, acks="all")
            await self.producer.start()
        await self.producer.send_and_wait("mall.events", json.dumps(envelope).encode(),
                                          key=envelope["aggregate"]["id"].encode())

    async def close(self):
        if self.producer is not None:
            await self.producer.stop()
