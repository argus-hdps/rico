"""Top-level package for Evryscope-Argus Transient Reporter."""

__author__ = """Hank Corbett"""
__email__ = "htc@unc.edu"
__all__ = ["get_logger", "config"]

import importlib.metadata
import logging
import os

from dotenv import load_dotenv

__version__ = importlib.metadata.version("argus-rico")

basedir = os.path.abspath(os.path.dirname(__file__))

if os.path.isfile(os.path.join(os.path.expanduser("~"), ".ricoenv")):
    load_dotenv(os.path.join(os.path.expanduser("~"), ".ricoenv"))
else:
    load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    """
    Configuration class for managing application settings.

    Attributes:
        LOCAL_ADDR (str): The local address to bind the application to. Defaults to "127.0.0.1" if not provided in the environment.
        KAFKA_ADDR (str): The address of the Kafka server. Defaults to "152.2.38.172" if not provided in the environment.
        KAFKA_PORT (str): The port of the Kafka server. Defaults to "9092" if not provided in the environment.
        HBEAT_TOPIC (str): The topic name for heartbeat messages in Kafka. Defaults to "rico-hearbeat" if not provided in the environment.
    """

    SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET") or None
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") or None
    SLACK_PORT = os.environ.get("SLACK_PORT") or 3000

    LOCAL_ADDR = os.environ.get("LOCAL_ADDR") or "127.0.0.1"
    INDEX_WORKERS = os.environ.get("INDEX_WORKERS") or 24

    KAFKA_ADDR = os.environ.get("KAFKA_ADDR") or "127.0.0.1"
    KAFKA_PORT = os.environ.get("KAFKA_PORT") or "9092"
    HBEAT_TOPIC = os.environ.get("HBEAT_TOPIC") or "rico.heartbeat"
    RAW_TOPIC_BASE = os.environ.get("RAW_TOPIC_BASE") or "rico.candidates.raw"
    EFTE_TOPIC_BASE = os.environ.get("EFTE_TOPIC_BASE") or "rico.efte.alerts"
    EVR_IMAGE_TOPIC = os.environ.get("EVR_IMAGE_TOPIC") or "rico.images.evr"

    MONGODB_URI = os.environ.get("MONGODB_URI") or None
    MONGO_DBNAME = os.environ.get("MONGO_DBNAME") or "hdps"

    EFTE_DB_ADDR = os.environ.get("EFTE_DB_ADDR") or "127.0.0.1"
    EFTE_DB_PORT = os.environ.get("EFTE_DB_PORT") or 5432
    EFTE_DB_NAME = os.environ.get("EFTE_DB_NAME") or "transients"
    EFTE_DB_USER = os.environ.get("EFTE_DB_USER") or None
    EFTE_DB_PASS = os.environ.get("EFTE_DB_PASS") or None

    WASABI_KEY_ID = os.environ.get("WASABI_KEY_ID") or None
    WASABI_SECRET_KEY = os.environ.get("WASABI_SECRET_KEY") or None
    WASABI_ENDPOINT = os.environ.get("WASABI_ENDPOINT") or None
    RICO_CACHE_DIR = os.environ.get("RICO_CACHE_DIR") or None
    if RICO_CACHE_DIR is None:
        RICO_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".rico_cache")
    if not os.path.isdir(RICO_CACHE_DIR):
        os.makedirs(RICO_CACHE_DIR)


config = Config()


def get_logger(name: str) -> logging.Logger:
    """
    Shortcut to grab a logger instance with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: A logger instance configured with the specified name.
    """

    logger = logging.getLogger(name)
    if not logger.handlers:
        # Prevent logging from propagating to the root logger
        logger.propagate = False
        logger.setLevel(("INFO"))
        console = logging.StreamHandler()
        logger.addHandler(console)
        formatter = logging.Formatter(
            "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
        )
        console.setFormatter(formatter)
    return logger


# For testing
get_logger(__name__).addHandler(logging.StreamHandler())

# Silenced
# get_logger(__name__).addHandler(logging.NullHandler())
