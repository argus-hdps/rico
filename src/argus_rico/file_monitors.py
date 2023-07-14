from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver


class EFTEWatcher:
    def __init__(self, watch_path: str, format="fits"):
        self.watch_path = watch_path
        self.file_format = "fits"

    def watch(self):
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
    pass
