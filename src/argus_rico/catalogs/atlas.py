__all__ = ["MissingDirectoryError", "ATLASRefcat2"]

import glob
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Union

import astropy.coordinates as crds
import astropy.units as u
import click
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pds
import pyarrow.feather as pf
import pyarrow.parquet as pq
from astropy_healpix import HEALPix

from .. import config, s3


class MissingDirectoryError(Exception):
    """Exception raised when a directory is missing.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message: str = "Tree basepath is not set!"):
        self.message = message
        super().__init__(self.message)


def haversine(
    lon1: np.ndarray, lat1: np.ndarray, lon2: np.ndarray, lat2: np.ndarray
) -> np.ndarray:
    """Calculate the great circle distance between two points on the earth.

    Args:
        lon1 (np.ndarray): Longitudes of the first points in decimal degrees.
        lat1 (np.ndarray): Latitudes of the first points in decimal degrees.
        lon2 (np.ndarray): Longitudes of the second points in decimal degrees.
        lat2 (np.ndarray): Latitudes of the second points in decimal degrees.

    Returns:
        np.ndarray: The great circle distances in degrees.
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2

    c = 2 * np.arcsin(np.sqrt(a))
    return np.rad2deg(c)


class ATLASRefcat2:
    def __init__(self):
        self.h4 = HEALPix(nside=4, order="nested", frame=crds.ICRS())
        self.h16 = HEALPix(nside=16, order="nested", frame=crds.ICRS())

        self.table: pa.Table = None
        self.dataset: str = None

        if os.path.isdir(os.path.join("/etc/rico/atlas_refcat2")):
            self.dataset = "/etc/rico/atlas_refcat2"

        else:
            if not os.path.isdir(os.path.join(config.RICO_CACHE_DIR, "atlas_refcat2")):
                if click.confirm(
                    "ATLAS RefCat not found, do you want to download it (82 GB)?"
                ):
                    s3share = s3.S3Share()
                    s3share.download_atlas()

                else:
                    raise MissingDirectoryError("ATLAS Refcat is not installed")
            self.dataset = os.path.join(config.RICO_CACHE_DIR, "atlas_refcat2")

    def radial(
        self,
        ra: float,
        dec: float,
        radius: float,
        min_g: float = 11.0,
        max_g: float = 16.0,
        return_area: bool = False,
        grab_closest: bool = False,
        as_pandas: bool = True,
    ) -> Union[pd.DataFrame, pa.Table]:
        """Perform radial search on the dataset.

        Args:
            ra (float): Right ascension in degrees.
            dec (float): Declination in degrees.
            radius (float): Radius of the search in degrees.
            min_g (float, optional): Minimum 'g' value for filtering. Defaults to 11.0.
            max_g (float, optional): Maximum 'g' value for filtering. Defaults to 16.0.
            return_area (bool, optional): Whether to return the area covered by the search.
                Defaults to True.
            grab_closest (bool, optional): Whether to return only the closest match.
                Defaults to False.
            as_pandas (bool, optional): Whether to return the result as a pandas DataFrame.
                If False, the result is returned as a pyarrow Table. Defaults to True.

        Returns:
            Union[pd.DataFrame, pa.Table]: The filtered dataset within the specified radius.
        """
        hpx_4 = self.h4.cone_search_lonlat(ra * u.deg, dec * u.deg, radius * u.deg)
        hpx_16 = self.h16.cone_search_lonlat(ra * u.deg, dec * u.deg, radius * u.deg)

        imfiles = []
        for i4 in hpx_4:
            files_4 = [
                glob.glob(
                    os.path.join(
                        self.dataset, str(i4) + "/" + str(i) + "/" + "*.feather"
                    )
                )
                for i in hpx_16
            ]
            imfiles += files_4
        imfiles = [x[0] for x in imfiles if len(x) > 0]

        if as_pandas:
            with ThreadPoolExecutor() as threads:
                t_res = threads.map(
                    self._from_featherfile_pandas,
                    zip(
                        imfiles,
                        [
                            [min_g, max_g],
                        ]
                        * len(imfiles),
                    ),
                )
            t = pd.concat(t_res)
            separations = haversine(t["ra"], t["dec"], ra, dec)
            t["separation"] = separations

            if grab_closest:
                t = t.iloc[[np.argmin(separations)]]
            else:
                t = t[separations < radius]

        else:
            with ThreadPoolExecutor() as threads:
                t_res = threads.map(
                    self._from_featherfile,
                    zip(
                        imfiles,
                        [
                            [min_g, max_g],
                        ]
                        * len(imfiles),
                    ),
                )

            t = pa.concat_tables(t_res)
            separations = haversine(t["ra"].to_numpy(), t["dec"].to_numpy(), ra, dec)
            t.append_column("separation", [pa.array(separations)])

            t = t.filter(separations < radius)

        if return_area:
            return t, np.pi * radius**2
        else:
            return t

    @staticmethod
    def _from_featherfile_pandas(packet: Tuple[str, List[float]]) -> pd.DataFrame:
        """Read a feather file and return the DataFrame after filtering.

        Args:
            packet (Tuple[str, List[float]]): A tuple containing the feather file path
                and the range of 'g' values for filtering.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        path, [min_g, max_g] = packet
        t = pf.read_feather(path)

        t = t[(t["g"] < max_g) & (t["g"] > min_g)]

        return t

    @staticmethod
    def _from_featherfile(packet: Tuple[str, List[float]]) -> pa.Table:
        """Read a feather file and return the Table.

        Args:
            packet (Tuple[str, List[float]]): A tuple containing the feather file path
                and dummy list.

        Returns:
            pa.Table: The Table read from the feather file.
        """
        path, [_, _] = packet
        t = pf.read_table(path)

        return t

    def to_parquet(self, outpath: str) -> None:
        """Write the Table to a parquet file.

        Args:
            outpath (str): The output path for the parquet file.
        """
        pq.write_table(self.table, outpath)

    def from_parquet(self, path: str) -> None:
        """Load a parquet file into the class.

        Args:
            path (str): The path to the parquet file.

        Raises:
            FileNotFoundError: If the parquet file at the given path is not found.
        """
        try:
            self.table = pq.read_table(path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Parquet file not found at path: {path}")

    def to_ds(self, outdir: str) -> None:
        """Write the Table to a dataset in feather format.

        Args:
            outdir (str): The output directory for the dataset.
        """
        part = pds.partitioning(
            pa.schema(
                [
                    ("h4", pa.int32()),
                    ("h16", pa.int32()),
                    # ("h32", pa.int32()),
                    # ("h64", pa.int32()),
                    # ("h256", pa.int32()),
                ]
            ),
        )
        pds.write_dataset(
            self.table,
            outdir,
            format="feather",
            max_partitions=786432,
            partitioning=part,
            max_open_files=786432,
        )

    def to_segment_ds(self, outdir: str, nside_base: int) -> None:
        """Write the Table to a segmented dataset in feather format.

        Args:
            outdir (str): The output directory for the segmented dataset.
            nside_base (int): The base nside value for segmentation.
        """
        part = pds.partitioning(
            pa.schema(
                [
                    ("h4", pa.int32()),
                    ("h16", pa.int32()),
                    ("h64", pa.int32()),
                    ("h256", pa.int32()),
                ]
            ),
        )
        pds.write_dataset(
            self.table,
            outdir,
            format="feather",
            max_partitions=786432,
            partitioning=part,
            max_open_files=786432,
        )
