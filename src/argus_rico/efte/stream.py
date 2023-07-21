__all__ = ["RawAlertStreamer"]

import io
import os
from typing import Any, Dict, List, Tuple
from uuid import uuid4

import astropy.table as tbl
import blosc
import fastavro as fa
import orjson
from confluent_kafka import KafkaException

from .. import config
from ..consumerB import Consumer
from ..producer import Producer

PATH = os.path.realpath(os.path.dirname(__file__))


class RawAlertStreamer(Producer):
    def __init__(self) -> None:
        """
        Initialize the RawAlertStreamer instance.

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


class EFTEAlertStreamer(Producer):
    def __init__(self) -> None:
        """
        Initialize the EFTEAlertStreamer instance.

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
        self.topic_base = config.EFTE_TOPIC_BASE

        # Parse alert schema
        named_schemas = {}
        with open(f"{PATH}/schemas/efte_alert.avsc", "rb") as f:
            alert_schema = orjson.loads(f.read())
        with open(f"{PATH}/schemas/efte_candidate.avsc", "rb") as f:
            candidate_schema = orjson.loads(f.read())
        with open(f"{PATH}/schemas/efte_xmatch.avsc", "rb") as f:
            xmatch_schema = orjson.loads(f.read())
        _ = fa.parse_schema(candidate_schema, named_schemas)
        _ = fa.parse_schema(xmatch_schema, named_schemas)
        self.parsed_alert_schema = fa.parse_schema(alert_schema, named_schemas)

    def _parse_catalog(
        self, catalog: tbl.Table, xmatches: List[Dict[str, List]]
    ) -> bytes:
        """
        Parses a catalog file and returns the serialized Avro data.

        Args:
            catalog_path (str): The path to the catalog file.

        Returns:
            bytes: The serialized Avro data.
            dict: Catalog metadata.
        """
        tab = catalog

        mjd = tab.meta["MJD"]
        camera_id = tab.meta["CCDDETID"]

        records = []
        for i, r in enumerate(tab):
            alert_data = {
                "schemavsn": self.parsed_alert_schema["version"],
                "publisher": "rico.efte_generator",
                "objectId": str(uuid4()),
            }

            stamp = blosc.compress(r["stamp"].tobytes())
            candidate = dict(r)
            candidate["stamp"] = stamp
            candidate["epoch"] = mjd
            candidate["camera"] = camera_id

            alert_data["candidate"] = candidate
            alert_data["xmatches"] = xmatches[i]

            records.append(alert_data)

        fo = io.BytesIO()
        fa.writer(fo, self.parsed_alert_schema, records)
        fo.seek(0)

        return fo.read()

    def push_alert(self, catalog: tbl.Table, xmatches: List[Dict[str, List]]) -> None:
        """
        Pushes data from a catalog file to a camera-specific topic.

        Args:
            catalog_path (str): The path to the catalog file.

        Returns:
            None

        """
        avro_data = self._parse_catalog(catalog, xmatches)
        topic = self.topic_base
        self.send_binary(avro_data, topic=topic)


class EFTEAlertReceiver(Consumer):
    def __init__(self, group: str) -> None:
        super().__init__(
            host=config.KAFKA_ADDR,
            port=config.KAFKA_PORT,
            topic=config.EFTE_TOPIC_BASE,
            group_id=group,
        )

    def poll_and_record(self) -> None:
        c = self.get_consumer()

        c.subscribe(self.topic)
        try:
            while True:
                event = c.poll(1.0)
                if event is None:
                    continue
                if event.error():
                    raise KafkaException(event.error())
                else:
                    # val = event.value().decode('utf8')
                    partition = event.partition()
                    print(f"Received from partition {partition}    ")
                    # consumer.commit(event)
        except KeyboardInterrupt:
            print("Canceled by user.")
        finally:
            c.close()
