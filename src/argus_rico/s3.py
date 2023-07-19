__all__ = ["S3AuthException", "S3Share"]
"""S3 Share module for handling Wasabi S3 interactions."""
import os
import tarfile
from typing import NoReturn

import boto3

from . import config


class S3AuthException(Exception):
    """Exception raised for S3 authentication errors."""

    pass


class S3Share:
    def __init__(self) -> None:
        """Initialize the S3Share class.

        Raises:
            S3AuthException: If Wasabi credentials are missing in ricoenv.
        """
        if config.WASABI_KEY_ID is None or config.WASABI_SECRET_KEY is None:
            raise S3AuthException("No Wasabi credentials in ricoenv")

        self.s3 = boto3.resource(
            "s3",
            aws_access_key_id=config.WASABI_KEY_ID,
            aws_secret_access_key=config.WASABI_SECRET_KEY,
            endpoint_url=config.WASABI_ENDPOINT,
        )

        self.vetnet_bucket = self.s3.Bucket("efte.vetnet")
        self.catalog_bucket = self.s3.Bucket("hera.catalogs")
        self.stamps_bucket = "efte.stamps"

    def upload_stamp(self, id: str) -> str:
        """
        Upload a stamp for to S3.

        Args:
            id (str): S3 key for the stamp (candidate ID)

        Returns:
            str: Pre-authenticated URL for the stamp file.
        """
        url = self.s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.stamps_bucket, "Key": "invoice.pdf"},
        )
        return url

    def download_vetnet(self) -> NoReturn:
        """Download Vetnet data from S3.

        Downloads the hypersky_v7_v0.tar.gz file from the S3 bucket,
        extracts its contents, and saves it in the cache directory.

        Raises:
            botocore.exceptions.ClientError: If the file download fails.
        """
        cached_path = os.path.join(
            os.path.expanduser("~"), ".rico_cache", "hypersky_v7_v0.tar.gz"
        )

        self.vetnet_bucket.download_file(
            "hypersky_v7_v0.tar.gz",
            cached_path,
        )
        outpath = os.path.dirname(cached_path)
        file = tarfile.open(cached_path)
        file.extractall(outpath)
        file.close()

    def download_atlas(self) -> NoReturn:
        """Download ATLAS-RefCat 2 data from S3.

        Downloads the atlas_feathercat.tar.gz file from the S3 bucket,
        extracts its contents, and saves it in the cache directory.

        Raises:
            botocore.exceptions.ClientError: If the file download fails.
        """
        cached_path = os.path.join(config.RICO_CACHE_DIR, "atlas_feathercat.tar.gz")

        self.catalog_bucket.download_file(
            "atlas_feathercat.tar.gz",
            cached_path,
        )
        outpath = os.path.dirname(cached_path)
        file = tarfile.open(cached_path)
        file.extractall(outpath)
        file.close()
