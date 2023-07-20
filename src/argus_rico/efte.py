__all__ = ["VetNet"]
"""Data ingest support for EFTE transient catalogs."""
import os
from typing import Tuple

import astropy.table as tbl
import astropy.visualization as viz
import numpy as np
import ray
import tensorflow as tf
import tensorflow.keras.models as models

from . import catalogs, efte_stream, s3


class VetNet:
    def __init__(self) -> None:
        """Initialize the Vetnet class.

        Loads the pretrained model and sets class variables.
        """
        try:
            if not os.path.isdir(os.path.join(os.path.expanduser("~"), ".rico_cache")):
                os.mkdir(os.path.join(os.path.expanduser("~"), ".rico_cache"))

            self.model = models.load_model(
                os.path.join(os.path.expanduser("~"), ".rico_cache", "hypersky_v7_v0")
            )
        except OSError:
            s3share = s3.S3Share()
            s3share.download_vetnet()
            self.model = models.load_model(
                os.path.join(os.path.expanduser("~"), ".rico_cache", "hypersky_v7_v0")
            )

        self.BATCH_SIZE: int  # The batch size for data processing
        self.AUTOTUNE: int = tf.data.AUTOTUNE  # The buffer size for prefetching
        self.zed = viz.ZScaleInterval()

    def prep_ds(self, ds: tf.data.Dataset) -> tf.data.Dataset:
        """Preprocess the input dataset.

        Batch the dataset and apply buffered prefetching.

        Args:
            ds (tf.data.Dataset): The input dataset.

        Returns:
            tf.data.Dataset: The preprocessed dataset.
        """
        # Batch all datasets
        ds = ds.batch(self.BATCH_SIZE)

        # Use buffered prefetching on all datasets
        return ds.prefetch(buffer_size=self.AUTOTUNE)

    def _normalize_triplet(self, data: np.ndarray) -> np.ndarray:
        """Perform stamp normalization. Processes the reference, science, and
        difference images separately.


        Args:
            data (np.ndarray): The input data for prediction.

        Returns:
            np.ndarray: Recursively normalized postage stamp cutout.
        """
        for i in range(data.shape[-1]):
            data[:, :, i] = self.zed(data[:, :, i])

        return data

    def _normalize_stamps(self, data: np.ndarray) -> np.ndarray:
        """Perform recursive stamp normalization. Processes the reference,
        science, and difference images separately.


        Args:
            data (np.ndarray): The input data for prediction.

        Returns:
            np.ndarray: Recursively normalized postage stamp cutouts.
        """
        for i in range(data.shape[0]):
            data[i, :, :, :] = self._normalize_triplet(data[i, :, :, :])

        return data

    def mc_predict(
        self, data: np.ndarray, n_posterior_draws: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Perform Monte Carlo prediction.

        Args:
            data (np.ndarray): The input data for prediction.
            n_posterior_draws (int): The number of posterior draws.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]: A tuple containing:
            - mean_pred (np.ndarray): The mean prediction.
            - low_pred (np.ndarray): The lower prediction bound.
            - high_pred (np.ndarray): The upper prediction bound.
            - confidence (np.ndarray): The confidence measure.
        """
        data = self._normalize_stamps(data)

        pred_dists = np.array(
            [self.model(data, training=False) for _ in range(n_posterior_draws)]
        )

        pred_dists[pred_dists == 0] += 1e-5
        pred_dists[pred_dists == 1] -= 1e-5

        entropy = (-1 * pred_dists * np.log2(pred_dists)) - (
            (1 - pred_dists) * np.log2(1 - pred_dists)
        )
        low_pred = np.rint(np.percentile(pred_dists, (50.0 - 95.4 / 2), axis=0))
        high_pred = np.rint(np.percentile(pred_dists, (50.0 + 95.4 / 2), axis=0))
        mean_pred = np.rint(np.mean(pred_dists, axis=0))

        confidence = 1 - (1 / n_posterior_draws) * np.sum(entropy, axis=0)

        return mean_pred, low_pred, high_pred, confidence


@ray.remote
class EFTECatalogProcessor:
    def __init__(self):
        """Initialize the EFTECatalogProcessor class."""
        self.vetnet = VetNet()
        self.atlas = catalogs.ATLASRefcat2()
        self.producer = efte_stream.EFTEAlertStreamer()

    def process(self, filepath: str) -> None:
        """Perform vetting and crossmatching for the given FITS table.

        Args:
            filepath (str): The path to the FITS table.

        Returns:
            Table: Returns the FITS table with normalized stamps, scores.
        """
        table: tbl.Table = tbl.Table.read(filepath, format="fits")

        stamps = table["stamp"].data
        mean_pred, _, _, confidence = self.vetnet.mc_predict(stamps, 10)

        table["vetnet"] = confidence[:, 0]
        table = table[mean_pred[:, 0] > 0.5]

        table = table[table["vetnet"] > 0.4]  # fairly arbitrary...
        if len(table) == 0:
            return

        crossmatches = []
        for r in table:
            phot = self.atlas.radial(
                r["ra"], r["dec"], 0.01, max_g=25, return_area=False
            )
            phot = phot.sort_values(by="separation")
            crossmatches.append(phot.to_dict(orient="records"))

        self.producer.push_alert(table, crossmatches)
