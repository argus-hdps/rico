__all__ = ["RawStreamer"]

import io
import os
from typing import Any, Dict, Tuple

import astropy.table as tbl
import blosc
import fastavro as fa
import orjson

from . import config
from .producer import Producer

PATH = os.path.realpath(os.path.dirname(__file__))


class RawStreamer(Producer):
    def __init__(self) -> None:
        """
        Initialize the RawStreamer instance.

        It inherits from the Producer class and configures the Kafka connection parameters
        using values from the config dictionary.

        This class is used for streaming raw candidate detections from the
        observatory to the Rico Kafka cluster.

        The host, port, and topic are retrieved from the config dictionary
        using the keys 'KAFKA_ADDR', 'KAFKA_PORT', and 'HBEAT_TOPIC' respectively.
        """
        super().__init__(
            host=config.KAFKA_ADDR,
            port=config.KAFKA_PORT,
        )
        self.topic_base = config.RAW_TOPIC_BASE

    def _parse_raw_catalog(self, catalog_path: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Parses a raw catalog file and returns the serialized Avro data.

        Args:
            catalog_path (str): The path to the catalog file.

        Returns:
            bytes: The serialized Avro data.
            dict: Catalog metadata.
        """
        tab = tbl.Table.read(catalog_path)

        mjd = tab.meta["MJD"]
        camera_id = tab.meta["CCDDETID"]

        records = []
        for r in tab:
            stamp = blosc.compress(r["stamp"].tobytes())
            record = dict(r)
            record["stamp"] = stamp
            record["epoch"] = mjd
            record["camera"] = camera_id

            records.append(record)

        with open(f"{PATH}/schemas/raw_candidate.avsc", "rb") as f:
            schema = orjson.loads(f.read())

        parsed_schema = fa.parse_schema(schema)

        fo = io.BytesIO()
        fa.writer(fo, parsed_schema, records)
        fo.seek(0)

        return fo.read(), tab.meta

    def push_from_catalog(self, catalog_path: str) -> None:
        """
        Pushes data from a catalog file to a camera-specific topic.

        Args:
            catalog_path (str): The path to the catalog file.

        Returns:
            None

        """
        avro_data, metadata = self._parse_raw_catalog(catalog_path)
        topic = self.topic_base + f'.{metadata["CCDDETID"]}'

        self.send_binary(avro_data, topic=topic)
