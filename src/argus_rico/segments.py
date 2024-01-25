import glob
import multiprocessing as mp
import operator
import os
import warnings
from functools import reduce

import astropy.coordinates as acrd
import astropy_healpix as ahpx
import click
import numpy as np
import orjson
import pyarrow as pa
import pyarrow.parquet as pq

from . import afits as arf
from . import config, fast_healpix


class SegmentArchiveException(Exception):
    """Exception raised SkyMap error.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Segment archive is corrupted."):
        self.message = message
        super().__init__(self.message)


class SegmentArchive:
    def __init__(self, root, load_index=True):
        self.root = root

        # Note: This should be pulled from a manifest in the root directory
        # of the data archive, which is not currently implemented.
        self.manifest = None
        self.nside_base = 32

        if self.nside_base == 32:  # Evryscope
            self.subdivs = [self.nside_base // 16, self.nside_base // 4]
        elif self.nside_base == 256:  # Argus
            self.subdivs = [
                self.nside_base // 64,
                self.nside_base // 16,
                self.nside_base // 4,
            ]
        else:
            raise SegmentArchiveException(
                f"Base NSide of SkyMap must be 32 (EVR) or 256 (Argus), got {self.nside_base}"
            )

        # NB: The following astropy lookups are used for pixel metadata
        # Actual geometry is done with the fast_healpix subpackage.
        self.hpix = ahpx.HEALPix(
            nside=self.nside_base,
            order="nested",
            frame=acrd.ICRS(),
        )

        self.subdiv_hpx = []
        for nside in self.subdivs:
            self.subdiv_hpx.append(
                ahpx.HEALPix(nside=nside, order="nested", frame=acrd.ICRS())
            )

        self.indexed = False
        if load_index:
            self._load_index()
        else:
            self.pixels = self._traverse()
        self._pixcache = None

    def _traverse(self):
        n_levels = len(self.subdivs) + 1

        # Traverse the skymap tree, find all full-qualified healpix
        fqhipix = glob.glob(os.path.join(self.root, "/".join(["??????"] * n_levels)))

        pixels = {}
        for fqi in fqhipix:
            ipix = str(int(fqi.split("/")[-1]))
            pixels[ipix] = {"path": fqi}
        return pixels

    def _index_ipix(self, pix):
        nights = glob.glob(os.path.join(self.pixels[pix]["path"], "????????.fits"))
        pixel_dict = {}
        pixel_dict[pix] = self.pixels[pix]
        pixel_dict[pix]["nights"] = {}
        for night in nights:
            if self._pixcache is not None and night in self._pixcache[pix]["nights"]:
                pixel_dict[pix]["nights"][night] = self._pixcache[pix]["nights"][night]
                continue
            night_dict = {
                "ntiles": 0,
                "ntiles_zweighted": 0,
                "filenames": [],
                "epochs": [],
                "data_start_byte": [],
                "data_size": [],
            }

            ahdulist = arf.open(night, get_byte_positions=True)
            tile_size = ahdulist[1].data.size
            for tile in ahdulist[1:]:
                night_dict["ntiles"] += 1
                night_dict["ntiles_zweighted"] += (
                    np.count_nonzero(tile.data) / tile_size
                )
                night_dict["filenames"].append(tile.header["ORIGNAME"])
                night_dict["epochs"].append(tile.header["DATE-OBS"])
                night_dict["data_start_byte"].append(tile.header["_BYTE_START"])
                night_dict["data_size"].append(tile.header["_NBYTES"])

            pixel_dict[pix]["nights"][night] = night_dict
        return pixel_dict

    def index(self):
        manifest_path = os.path.join(self.root, "manifest.json")
        summary_path = os.path.join(self.root, "summary.parquet")

        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                self._pixcache = orjson.loads(f.read())
        else:
            self._pixcache = None

        pix_ids = sorted(list(self.pixels.keys()))
        n_ipix = len(pix_ids)

        pool = mp.Pool(config.INDEX_WORKERS)

        pixel_dicts = []
        with click.progressbar(
            pool.imap_unordered(self._index_ipix, pix_ids),
            label="Indexing: ",
            length=len(pix_ids),
        ) as pbar:
            for p in pbar:
                pixel_dicts.append(p)

        self.pixels = reduce(operator.ior, pixel_dicts, {})
        self._pixcache = None

        pool.close()
        pool.join()

        for pix in self.pixels:
            total_tiles = 0
            total_tiles_weighted = 0
            for night in self.pixels[pix]["nights"]:
                total_tiles += self.pixels[pix]["nights"][night]["ntiles"]
                total_tiles_weighted += self.pixels[pix]["nights"][night][
                    "ntiles_zweighted"
                ]
            self.pixels[pix]["total_tiles"] = total_tiles
            self.pixels[pix]["total_tiles_weighted"] = total_tiles_weighted

        with open(manifest_path, "w") as f:
            f.write(orjson.dumps(self.pixels).decode("utf-8"))

        # Finally, write a summary table
        t = np.zeros(n_ipix, dtype=int)
        wt = np.zeros(n_ipix, dtype=np.float32)
        ipix = np.zeros(n_ipix, dtype=int)
        ra = np.zeros(n_ipix, dtype=np.float32)
        dec = np.zeros(n_ipix, dtype=np.float32)

        fast_healpixer = fast_healpix.FastHealpix()

        for i, pix in enumerate(self.pixels):
            t[i] = self.pixels[pix]["total_tiles"]
            wt[i] = self.pixels[pix]["total_tiles_weighted"]
            ipix[i] = pix
            ra[i], dec[i] = fast_healpixer.healpix_to_radec(
                int(pix), self.nside_base, 0.0, 0.0
            )

        summary_table = pa.Table.from_pydict(
            {
                "ipix": ipix,
                "ra": ra,
                "dec": dec,
                "n_tiles": t,
                "n_tiles_density_weighted": wt,
            }
        )
        pq.write_table(summary_table, summary_path)
        self.indexed = True

        return self.pixels

    def _load_index(self):
        manifest_path = os.path.join(self.root, "manifest.json")
        if not os.path.isfile(manifest_path):
            warnings.warn("No manifest file found! Do you need to index this archive?")
            return False
        with open(os.path.join(self.root, "manifest.json"), "rb") as f:
            manifest = orjson.loads(f.read())
        self.indexed = True
        self.pixels = manifest

    def get_ipix_path(self, ipix):
        fast_healpixer = fast_healpix.FastHealpix()

        ra, dec = fast_healpixer.healpix_to_radec(
            ipix,
            self.nside_base,
            0.0,
            0.0,
        )

        path = self.root
        for nside in self.subdivs:
            subhealpix = fast_healpixer.radec_to_healpix(ra, dec, nside)

            path = os.path.join(path, f"{subhealpix:06}")
        path = os.path.join(path, f"{ipix:06}")
        return path

    def index_to_dataframe(self):
        flat_dict = {
            "ipix": [],
            "filename": [],
            "startbyte": [],
            "bytesize": [],
            "epochs": [],
        }
        for ipix in self.pixels:
            nights = self.pixels[ipix]["nights"]
            for night in nights:
                epochs = self.pixels[ipix]["nights"][night]["epochs"]
                for i in range(len(epochs)):
                    flat_dict["ipix"].append(ipix)
                    flat_dict["filename"].append(night)
                    flat_dict["startbyte"].append(
                        self.pixels[ipix]["nights"][night]["data_start_byte"][i]
                    )
                    flat_dict["bytesize"].append(
                        self.pixels[ipix]["nights"][night]["data_size"][i]
                    )
                    flat_dict["epochs"].append(
                        self.pixels[ipix]["nights"][night]["epochs"][i]
                    )

        df = pa.Table.from_pydict(flat_dict).to_pandas()
        return df
