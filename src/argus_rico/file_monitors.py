__all__ = ["EFTEWatcher", "EFTECatalogHandler"]

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import get_logger

log = get_logger(__name__)


class EFTEWatcher:
    def __init__(self, watch_path: str, format="fits") -> None:
        self.watch_path = watch_path

    def watch(self) -> None:
        event_handler = EFTECatalogHandler()
        observer = PollingObserver()

        observer.schedule(event_handler, self.watch_path, recursive=False)
        observer.start()

        try:
            while observer.isAlive():
                observer.join(1)
        finally:
            observer.stop()
            observer.join()


class EFTECatalogHandler(FileSystemEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        filepath = event.src_path
        if filepath[-4] != ".cat":
            return
