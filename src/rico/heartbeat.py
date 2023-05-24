__all__ = ["RicoHeartBeat"]

import datetime
import threading

from . import config
from .producer import Producer


class RicoHeartBeat(Producer):
    def __init__(self) -> None:
        """
        Initialize the RicoHeartBeat instance.

        It inherits from the Producer class and configures the Kafka connection parameters
        using values from the config dictionary.

        The host, port, and topic are retrieved from the config dictionary
        using the keys 'KAFKA_ADDR', 'KAFKA_PORT', and 'HBEAT_TOPIC' respectively.
        """
        super().__init__(
            host=config.KAFKA_ADDR, port=config.KAFKA_PORT, topic=config.HBEAT_TOPIC
        )

    def send_heartbeat(self) -> None:
        """
        Send a heartbeat message to the Kafka topic.

        The message is a dictionary containing the current UTC time.
        """
        self.send({"utc": datetime.datetime.utcnow()})

    def start(self, rate: int = 30) -> None:
        """
        Start sending heartbeat messages periodically.

        Args:
            rate (int): The rate at which heartbeat messages should be sent, in seconds.
                        Defaults to 30 seconds.
        """
        threading.Timer(rate, self.send_heartbeat).start()
