"""Top-level package for Evryscope-Argus Transient Reporter."""

__author__ = """Hank Corbett"""
__email__ = "htc@unc.edu"
__version__ = "0.1.0"

import logging
import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    LOCAL_ADDR = os.environ.get("LOCAL_ADDR") or "127.0.0.1"

    KAFKA_ADDR = os.environ.get("KAFKA_ADDR") or "152.2.38.172"
    KAFKA_PORT = os.environ.get("KAFKA_ADDR") or "152.2.38.172"


c = Config()


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
