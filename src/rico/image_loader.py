import glob
import os
from typing import Any, Dict, Union

import astropy.io.fits as fits
from pymongo import MongoClient

from . import config, models
from .models import fitspath_to_constructor
from .producer import Producer


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

    def load_fits(self, path: str) -> None:
        """
        Load FITS file data into the MongoDB collection.

        Args:
            path (str): Path to the FITS file.

        Returns:
            None
        """
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
