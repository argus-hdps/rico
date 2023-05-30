from typing import Any, Dict, Optional, Union
from uuid import uuid4

import confluent_kafka as ck
import orjson

from . import get_logger


class Producer:
    def __init__(
        self,
        host: str,
        port: Union[int, str],
    ) -> None:
        """
        Initialize the Producer instance.

        Args:
            host (str): The hostname or IP address of the Kafka broker.
            port (Union[int, str]): The port number of the Kafka broker.
            topic (str): The name of the topic to produce messages to.
        """
        self.p = ck.Producer({"bootstrap.servers": f"{host}:{port}"})
        self.log = get_logger(__name__)

    def delivery_report(self, err: Optional[ck.KafkaError], msg: ck.Message) -> None:
        """
        Reports the failure or success of a message delivery.

        Args:
            err (Optional[ck.KafkaError]): The error that occurred, or None on success.
            msg (ck.Message): The message that was produced or failed.

        Note:
            In the delivery report callback, the Message.key() and Message.value()
            will be in binary format as encoded by any configured Serializers and
            not the same object that was passed to produce().
            If you wish to pass the original object(s) for key and value to the delivery
            report callback, we recommend using a bound callback or lambda where you pass
            the objects along.
        """
        if err is not None:
            self.log.error(f"Delivery failed for User record {msg.key()}: {err}")
            return
        self.log.info(
            f"Record {msg.key()} successfully produced to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )

    def send_json(self, message: Dict[Any, Any], topic: str) -> None:
        """
        Send a JSON message to the Kafka topic.

        Args:
            message (dict): The message to be sent, represented as a dictionary.
            topic (str): The name of the topic to send the message to.
        """
        self.p.produce(
            topic=topic,
            key=str(uuid4()),
            value=orjson.dumps(message),
            on_delivery=self.delivery_report,
        )
        self.p.flush()

    def send_binary(self, payload: bytes, topic: str) -> None:
        """
        Send a binary payload to the Kafka topic.

        Args:
            payload (bytes): The payload to be sent, represented as a bytestring.
            topic (str): The name of the topic to send the payload to.
        """
        self.p.produce(
            topic=topic,
            key=str(uuid4()),
            value=payload,
            on_delivery=self.delivery_report,
        )
        self.p.flush()
