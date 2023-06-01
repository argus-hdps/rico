import glob
import os
from typing import Any, Dict

from pymongo import MongoClient

from . import config, models


class EVRImageLoader:
    """Class for loading EVRImage data into a MongoDB collection."""

    def __init__(self, create_client: bool = True) -> None:
        """
        Initialize EVRImageLoader.

        Args:
            None

        Returns:
            None
        """
        self.client: MongoClient[Dict[str, Any]]

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
        if self.client is None:
            self.client = MongoClient(config.MONGODB_URI, uuidRepresentation="standard")
        images = glob.glob(os.path.join(dirname, "*.fits"))

        for image in images:
            self.load_fits(image)
