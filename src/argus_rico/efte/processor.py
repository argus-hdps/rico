"""Ray-parallelizable EFTE catalog reducer."""

import os

import astropy.table as tbl
import ray

from .. import catalogs, config, get_logger, utils
from .stream import EFTEAlertStreamer

if config.RICO_WITH_TF:
    from .vetnet import VetNet


@ray.remote
class EFTECatalogProcessor:
    def __init__(self):
        """Initialize the EFTECatalogProcessor class."""
        if config.RICO_WITH_TF:
            self.vetnet = VetNet()
        self.atlas = catalogs.ATLASRefcat2()
        self.producer = EFTEAlertStreamer()

        self.log = get_logger(__name__)

    def process(self, filepath: str) -> None:
        """Perform vetting and crossmatching for the given FITS table.

        Args:
            filepath (str): The path to the FITS table.

        Returns:
            Table: Returns the FITS table with normalized stamps, scores.
        """
        clock = utils.Timer(log=self.log)
        name = os.path.basename(filepath)
        table: tbl.Table = tbl.Table.read(filepath, format="fits")
        clock.ping(f"Read {len(table)} candidates from {name}")

        stamps = table["stamp"].data
        if config.RICO_WITH_TF:
            mean_pred, _, _, confidence = self.vetnet.mc_predict(stamps, 10)
            clock.ping(f"Vetted candidates from {name}")

            table["vetnet_score"] = confidence[:, 0]
            table = table[mean_pred[:, 0] > 0.5]
            table = table[table["vetnet_score"] > 0.4]  # fairly arbitrary...

        clock.ping(f"Reporting {len(table)} candidates in {name}")

        if len(table) == 0:
            return
        crossmatches = []
        for r in table:
            phot = self.atlas.radial(
                r["ra"], r["dec"], 0.01, max_g=25, return_area=False
            )
            phot = phot.sort_values(by="separation")
            crossmatches.append(phot.to_dict(orient="records"))

        clock.ping(f"Xmatched {name} with ATLAS Refcat")

        self.producer.push_alert(table, crossmatches)
