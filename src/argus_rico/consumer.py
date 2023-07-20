from typing import Any, Dict, Optional, Union
from __future__ import print_function
from uuid import uuid4
import confluent_kafka as ck
import orjson
from . import get_logger
from . import avroUtils
import io
import time
from ast import literal_eval

#Random stuff that I'm not sure we need, but putting it here just in case
#schema_path = 'your_avro_schema_file.avsc'
#data_file_path = 'your_avro_data_file.avro'

# Create Avro schema reader
#schema = open(schema_path, "rb").read()
#avro_reader = DatumReader(schema)
#----------------------------------------
__all__ = ['EopError', 'AlertConsumer']


class AlertError(Exception):
    """Base class for exceptions in this module.
    """
    pass


class EopError(AlertError):
    """Exception raised when reaching end of partition.

    Parameters
    ----------
    msg : Kafka message
        The Kafka message result from consumer.poll().
    """
    def __init__(self, msg):
        message = 'topic:%s, partition:%d, status:end, ' \
                  'offset:%d, key:%s, time:%.3f\n' \
                  % (msg.topic(), msg.partition(),
                     msg.offset(), str(msg.key()), time.time())
        self.message = message

    def __str__(self):
        return self.message
    
class Consumer(object):
    """Creates an alert stream Kafka consumer for a given topic.

    Parameters
    ----------
    topic : `str`
        Name of the topic to subscribe to.
    schema_files : Avro schema files
        The reader Avro schema files for decoding data. Optional.
    **kwargs
        Keyword arguments for configuring confluent_kafka.Consumer().
    """

    def __init__(self, topic, schema_files=None, **kwargs):
        self.topic = topic
        self.kafka_kwargs = kwargs
        if schema_files is not None:
            self.alert_schema = avroUtils.combineSchemas(schema_files)

    def __enter__(self):
        self.c = confluent_kafka.Consumer(**self.kafka_kwargs)
        self.c.subscribe([self.topic])
        return self

    def __exit__(self, type, value, traceback):
        # FIXME should be properly handling exceptions here, but we aren't
        self.c.close()

    def poll(self, decode=False, verbose=True):
        """Polls Kafka broker to consume topic.

        Parameters
        ----------
        decode : `boolean`
            If True, decodes data from Avro format.
        verbose : `boolean`
            If True, returns every message. If False, only raises EopError.
        """
        msg = self.c.poll(timeout=1)

        if msg:
            if msg.error():
                raise EopError(msg)
            else:
                if verbose is True:
                    if decode is True:
                        return self.decodeMessage(msg)
                    else:
                        ast_msg = literal_eval(str(msg.value(), encoding='utf-8'))
                        return ast_msg
        else:
            try:
                raise EopError(msg)
            except AttributeError:
                pass
        return

    def decodeMessage(self, msg):
        """Decode Avro message according to a schema.

        Parameters
        ----------
        msg : Kafka message
            The Kafka message result from consumer.poll().

        Returns
        -------
        `dict`
            Decoded message.
        """
        message = msg.value()
        try:
            bytes_io = io.BytesIO(message)
            decoded_msg = avroUtils.readSchemaData(bytes_io)
            #decoded_msg = avroUtils.readAvroData(bytes_io, self.alert_schema)
            #decoded_msg = avro.io.BinaryDecoder(bytes_io) #use this or line above
            #recorded_msg = avro_reader.read(decoded_msg)
            #print(json.dumps(recorded_msg,indent=4) #needed? not needed?
            
        except AssertionError:
            bytes_io = io.BytesIO(message)
            decoded_msg = None
        except IndexError:
            literal_msg = literal_eval(str(message, encoding='utf-8'))  # works to give bytes
            bytes_io = io.BytesIO(literal_msg)  # works to give <class '_io.BytesIO'>
            decoded_msg = avroUtils.readSchemaData(bytes_io)  # yields reader
        return decoded_msg
