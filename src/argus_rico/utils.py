__all__ = ["Timer"]

import time


class Timer:
    def __init__(self, log=None):
        self.start_time = time.perf_counter()
        self.last_ping = time.perf_counter()
        self.log = log

    def start(self):
        """Total runtime start."""
        self.start_time = time.perf_counter()

    @property
    def t(self):
        """Runtime relative to start."""
        return time.perf_counter() - self.start_time

    @property
    def t_since_last_ping(self):
        """Runtime relative to the last ping."""
        return time.perf_counter() - self.last_ping

    def ping(self, message):
        if self.log is not None:
            self.log.info(
                f"@ {self.t * 1000:0.0f} ms ({self.t_since_last_ping * 1000:0.0f} ms delta): {message}",
            )
        self.last_ping = time.perf_counter()
