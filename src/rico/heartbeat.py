__all__ = ["RicoHeartBeat"]

import datetime
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from . import config
from .producer import Producer


class RepeatTimer(threading.Timer):
    finished: threading.Event
    interval: float
    function: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]

    def run(self) -> None:
        while not self.finished.wait(self.interval):
            assert self.function is not None
            assert self.args is not None
            assert self.kwargs is not None
            self.function(*self.args, **self.kwargs)


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
            host=config.KAFKA_ADDR,
            port=config.KAFKA_PORT,
        )
        self.heartbeat_thread: Optional[RepeatTimer] = None

    def send_heartbeat(self) -> None:
        """
        Send a heartbeat message to the Kafka topic.

        The message is a dictionary containing the current UTC time.
        """
        self.send_json({"utc": datetime.datetime.utcnow()}, config.HBEAT_TOPIC)

    def start(self, rate: int = 30) -> None:
        """
        Start sending heartbeat messages periodically.

        Args:
            rate (int): The rate at which heartbeat messages should be sent, in seconds.
                        Defaults to 30 seconds.
        """
        self.heartbeat_thread = RepeatTimer(rate, self.send_heartbeat)
        self.heartbeat_thread.start()

    def stop(self) -> None:
        """
        Stop sending heartbeat messages periodically.
        """
        if self.heartbeat_thread is not None:
            self.heartbeat_thread.cancel()
