__all__ = ["EFTEAlertReceiver", "EFTEAlertStreamer"]

import base64
import io
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

import astropy.table as tbl
import blosc
import fastavro as fa
import orjson
import pandas as pd
from confluent_kafka import KafkaException

from .. import config, get_logger
from ..consumer import Consumer
from ..producer import Producer

PATH = os.path.realpath(os.path.dirname(__file__))


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

        self.parsed_alert_schema = fa.schema.load_schema(
            f"{PATH}/schemas/efte.alert.avsc"
        )

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

        if "MJD" not in tab.meta:
            tab.meta["MJD"] = 60000.1
        if "CCDDETID" not in tab.meta:
            tab.meta["CCDDETID"] = "ML3103817"

        mjd = tab.meta["MJD"]
        camera_id = tab.meta["CCDDETID"]

        records = []
        for i, r in enumerate(tab):
            alert_data = {
                "schemavsn": self.parsed_alert_schema["version"],
                "publisher": "rico.efte_generator",
                "objectId": str(uuid4()),
            }

            stamp = blosc.compress(r["stamp"].data.tobytes())

            candidate = dict(r)
            candidate["stamp_bytes"] = stamp
            candidate["epoch"] = mjd
            candidate["camera"] = camera_id

            alert_data["candidate"] = candidate
            alert_data["xmatch"] = xmatches[i]

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
    def __init__(
        self, group: str, output_path: str, filter_path: Optional[str] = None
    ) -> None:
        """Initialize the EFTEAlertReceiver class.

        Args:
            group (str): The Kafka consumer group ID.
            output_path (str): The path where filtered candidate data will be written.
            filter_path (Optional[str]): The path to the text file containing filter conditions for xmatch data.
                If provided, candidates will be filtered based on the conditions in the file.
                Each condition should be in the format: 'column_name operator value'.
        """
        super().__init__(
            host=config.KAFKA_ADDR,
            port=config.KAFKA_PORT,
            topic=config.EFTE_TOPIC_BASE,
            group_id=group,
        )

        self.parsed_alert_schema = fa.schema.load_schema(
            f"{PATH}/schemas/efte.alert.avsc"
        )
        self.filter_path = filter_path
        self.output_path = output_path
        self.log = get_logger(__name__)

    def poll_and_record(self) -> None:
        """Start polling for Kafka messages and process the candidates based on filter conditions."""
        c = self.get_consumer()

        c.subscribe(
            [
                self.topic,
            ]
        )
        try:
            while True:
                event = c.poll(1.0)
                if event is None:
                    continue
                if event.error():
                    raise KafkaException(event.error())
                else:
                    alerts = self._decode(event.value())
                    self._filter_to_disk(alerts)

        except KeyboardInterrupt:
            print("Canceled by user.")
        finally:
            c.close()

    def _decode(self, message: bytes) -> List[Dict[str, Any]]:
        """Decode the AVRO message into a list of dictionaries.

        Args:
            message (bytes): The AVRO message received from Kafka.

        Returns:
            List[Dict[str, Any]]: A list of candidate dictionaries.
        """
        stringio = io.BytesIO(message)
        stringio.seek(0)

        records = []
        for record in fa.reader(stringio):
            records.append(record)
        return records

    def _write_candidate(self, alert: Dict[str, Any]) -> None:
        """Write the candidate data to a JSON file.

        Args:
            candidate (Dict[str, Any]): The candidate dictionary to be written to the JSON file.
        """
        alert["candidate"]["stamp_bytes"] = base64.b64encode(
            alert["candidate"]["stamp_bytes"]
        ).decode("utf-8")
        with open(
            os.path.join(self.output_path, f"{alert['objectId']}.json"), "wb"
        ) as f:
            f.write(orjson.dumps(alert))
        self.log.info(f'New candidate: {alert["objectId"]}.json')

    def _filter_to_disk(self, alerts: List[Dict[str, Any]]) -> None:
        """Filter the candidates based on the specified filter conditions.

        Args:
            candidates (List[Dict[str, Any]]): The list of candidate dictionaries to be filtered.

        Note:
            If the 'filter_path' is provided, the candidates will be filtered based on the conditions
            specified in the text file. If 'xmatch' field is empty or 'filter_path' is not provided,
            all candidates will be written to the output.
        """
        if self.filter_path is not None:
            with open(self.filter_path, "r") as file:
                filter_conditions = file.read().splitlines()
            filter_conditions = [f for f in filter_conditions if len(f) > 3]

        for alert in alerts:
            if self.filter_path is not None:
                if len(alert["xmatch"]) > 0:
                    xmatch = pd.DataFrame.from_records(alert["xmatch"])
                    xmatch["g-r"] = xmatch["g"] - xmatch["r"]
                    for condition in filter_conditions:
                        column_name, operator, value = condition.split()
                        xmatch = xmatch.query(f"{column_name} {operator} {value}")
                    if len(xmatch) > 0:
                        self._write_candidate(alert)
                else:
                    return
            else:
                self._write_candidate(alert)
