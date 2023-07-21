"""(very thin) wrapper for running EFTE CLI utilities programmatically in a thread"""
import subprocess
import threading
from typing import Optional


class EFTERunner(threading.Thread):
    """A class representing a thread that runs a command using subprocess."""

    def __init__(self) -> None:
        """Initialize the EFTERunner thread."""
        self.stdout: Optional[bytes] = None
        self.stderr: Optional[bytes] = None
        threading.Thread.__init__(self)

    def run(self, command: str) -> None:
        """Execute the specified command in a separate thread.

        Args:
            command (str): The command to be executed.

        Returns:
            None.
        """
        p = subprocess.Popen(
            command.split(), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self.stdout, self.stderr = p.communicate()
