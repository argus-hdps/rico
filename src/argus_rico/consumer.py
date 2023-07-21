from typing import Union

import confluent_kafka as ck

from . import get_logger


class Consumer:
    def __init__(
        self,
        host: str,
        port: Union[int, str],
        group_id: str,
        topic: str,
    ) -> None:
        """Initialize the Consumer class.

        Args:
            host (str): The Kafka broker host.
            port (Union[int, str]): The Kafka broker port.
            group_id (str): The Kafka consumer group ID.
            topic (str): The Kafka topic to consume messages from.
        """
        # Unlike producer, consumer is created on poll
        self.config = {
            "bootstrap.servers": f"{host}:{port}",
            "group.id": group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": "latest",
        }

        self.log = get_logger(__name__)
        self.topic = topic
        self.polling = False

    def get_consumer(self) -> ck.Consumer:
        """Create and return a new Kafka consumer instance.

        Returns:
            ck.Consumer: A new Kafka consumer instance configured with the specified settings.
        """
        return ck.Consumer(self.config)
