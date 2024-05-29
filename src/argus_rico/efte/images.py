__all__ = ["images_containing", "get_image_meta", "EVRImageProducer", "EVRImageLoader"]

import datetime
import glob
import os
from typing import Any, Dict, Optional, Union

import astropy.io.fits as fits
import orjson
import pandas as pd
import pymongoarrow.monkey
from pymongo import MongoClient
from pymongoarrow.api import Schema

from .. import config
from ..producer import Producer
from . import models
from .models import fitspath_to_constructor

pymongoarrow.monkey.patch_all()


def images_containing(
    ra: float, dec: float, date_start: datetime.datetime, date_end: datetime.datetime
) -> pd.DataFrame:
    """
    Retrieve images containing a given position within a specified time range.

    Args:
        ra (float): Right ascension (ICRS) of the target position.
        dec (float): Declination (ICRS) of the target position.
        date_start (datetime.datetime): Start date of the time range.
        date_end (datetime.datetime): End date of the time range.

    Returns:
        pd.DataFrame: A DataFrame containing the retrieved images.

    """
    client = MongoClient(config.MONGODB_URI)
    collection = client[config.MONGO_DBNAME].evr_images
    images = collection.find_pandas_all(
        {
            "$and": [{"rawpath": {"$ne": None}}, {"wcspath": {"$ne": None}}],
            "footprint": {
                "$geoIntersects": {
                    "$geometry": {"type": "Point", "coordinates": [ra - 180.0, dec]}
                }
            },
            "obstime": {"$gte": date_start, "$lte": date_end},
            "image_type": "object",
        },
        schema=Schema(
            {
                "obstime": datetime.datetime,
                "image_type": str,
                "camera": str,
                "rawpath": str,
                "wcspath": str,
            }
        ),
    )
    return images


def get_image_meta(
    path: str,
) -> Dict[str, Any]:
    """
    Retrieve image metadata by filename.

    Args:
        path (str): Filename for the image

    Returns:
        Dict: Dictionary of image metadata

    """

    basename = os.path.basename(path).split(".")[0]

    client = MongoClient(config.MONGODB_URI)
    collection = client[config.MONGO_DBNAME].evr_images
    image = collection.find_one({"basename": basename})
    return image


class EVRImageProducer(Producer):
    """
    A Kafka producer for sending EVR images.

    Args:
        None

    Attributes:
        host (str): The Kafka host address.
        port (int): The Kafka port number.

    """

    def __init__(self) -> None:
        """
        Initialize the EVRImageProducer.

        Args:
            None

        Returns:
            None

        """
        super().__init__(
            host=config.KAFKA_ADDR,
            port=config.KAFKA_PORT,
        )

    def send_image(self, image: Union[str, fits.HDUList]) -> None:
        """
        Send an image to the EVR image topic.

        Args:
            image (Union[str, fits.HDUList]): The image to be sent. It can be either a string representing the
                path to a FITS file or a `fits.HDUList` object.

        Returns:
            None

        """
        image_dict = fitspath_to_constructor(image)
        self.send_json(image_dict, config.EVR_IMAGE_TOPIC)


class EVRNightSerializer:
    """Class for serializing EVRImage data into a JSON index."""

    def _dump_img(self, image: Union[str, fits.HDUList]) -> dict:
        """Load image, parse with Pydantic model, then dump to a dict.

        Args:
            image (Union[str, fits.HDUList]): The image to be sent. It can be either a string representing the
                path to a FITS file or a `fits.HDUList` object.

        Returns:
            A dictionary of image metadata.
        """
        img_model = models.EVRImage.from_fits(image)
        return img_model.model_dump()

    def load_directory(self, dirname: str, write: Optional[bool] = False) -> None:
        """
        Summarize all FITS files from a directory into a single JSON index.
        Convenience function, just loops over a glob result.

        Args:
            dirname (str): Directory path containing FITS files.
            write (bool): Write to file.

        Returns:
            Dictionary of all image metadata.
        """
        night_name = os.path.dirname(dirname).split("/")[-1]

        images = glob.glob(os.path.join(dirname, "*.fits"))
        out_dict = {}
        for image in images:
            out_dict[image] = self._dump_img(image)
        out_dict = {night_name: out_dict}

        if write:
            with open(
                os.path.join(
                    os.path.abspath(os.path.join(dirname, os.pardir)),
                    f"{night_name}.json",
                ),
                "w",
            ) as f:
                f.write(orjson.dumps(self.pixels).decode("utf-8"))
        return out_dict


class EVRImageLoader:
    """Class for loading EVRImage data into a MongoDB collection."""

    def __init__(self, create_client: bool = True) -> None:
        """
        Initialize EVRImageLoader.

        Args:
            create_client (bool): Whether to create a MongoDB client. Default is True.

        Returns:
            None
        """
        self.client: MongoClient[Dict[str, Any]]
        self.client_loaded: bool = create_client

        if create_client:
            self.client = MongoClient(config.MONGODB_URI, uuidRepresentation="standard")

    def load_fits(self, path: str, calibration: Optional[bool] = False) -> None:
        """
        Load FITS file metadata into the MongoDB collection.

        Args:
            path (str): Path to the FITS file.
            calibration (Optional[str]): True if image is master calibration frame

        Returns:
            None
        """
        if calibration:
            img_coll = self.client[config.MONGO_DBNAME].evr_calibs
        else:
            img_coll = self.client[config.MONGO_DBNAME].evr_images

        db_img = img_coll.find_one({"basename": os.path.basename(path).split(".")[0]})
        if db_img is None:
            img_new = models.EVRImage.from_fits(path)
            _ = img_coll.insert_one(img_new.dict())
        else:
            img_existing = models.EVRImageUpdate.from_fits(path)
            _ = img_coll.update_one(
                {"_id": db_img["_id"]}, {"$set": img_existing.dict(exclude_unset=True)}
            )

    def load_directory(self, dirname: str) -> None:
        """
        Load all FITS files from a directory into the MongoDB collection.
        Convenience function, just loops over a glob result.

        Args:
            dirname (str): Directory path containing FITS files.

        Returns:
            None
        """
        if not self.client_loaded:
            self.client = MongoClient(config.MONGODB_URI, uuidRepresentation="standard")
        images = glob.glob(os.path.join(dirname, "*.fits"))

        for image in images:
            self.load_fits(image)
