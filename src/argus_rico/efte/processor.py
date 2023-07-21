"""Ray-parallelizable EFTE catalog reducer."""
import astropy.table as tbl
import ray

from .. import catalogs
from .stream import EFTEAlertStreamer
from .vetnet import VetNet


@ray.remote
class EFTECatalogProcessor:
    def __init__(self):
        """Initialize the EFTECatalogProcessor class."""
        self.vetnet = VetNet()
        self.atlas = catalogs.ATLASRefcat2()
        self.producer = EFTEAlertStreamer()

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
