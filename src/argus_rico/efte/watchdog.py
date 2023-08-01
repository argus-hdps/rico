__all__ = ["EFTEWatcher", "EFTECatalogHandler"]

import os
import time
from collections import defaultdict

import ray
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from .. import get_logger
from .processor import EFTECatalogProcessor


class EFTEWatcher:
    def __init__(self, watch_path: str) -> None:
        """Initialize the EFTEWatcher class.

        Args:
            watch_path (str): The path to the directory to watch for catalog files.
            format (str, optional): The format of catalog files. Defaults to "fits".
        """
        self.watch_path = os.path.abspath(watch_path)

    def watch(self) -> None:
        """Start watching the specified directory for catalog files."""
        ray.init()
        event_handler = EFTECatalogHandler()
        observer = PollingObserver()

        observer.schedule(event_handler, self.watch_path, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


class EFTECatalogHandler(FileSystemEventHandler):
    def __init__(self):
        """Initialize the EFTECatalogHandler class."""
        self.efte_processors = defaultdict(EFTECatalogProcessor.remote)
        self.log = get_logger(__name__)

    def on_created(self, event: FileSystemEvent) -> None:
        """Process the newly created catalog file.

        Args:
            event (FileSystemEvent): The event object representing the file creation.

        Returns:
            None: This method does not return any value; it processes the catalog file.
        """
        filepath = event.src_path

        if filepath[-4:] != ".cat":
            return
        camera_id = os.path.basename(filepath)[:9]

        self.log.info(f"New cat for {camera_id}: {filepath}")

        self.efte_processors[camera_id].process.remote(filepath)
