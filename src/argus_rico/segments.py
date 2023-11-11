import glob
import os

import astropy.coordinates as acrd
import astropy_healpix as ahpx
import click
import orjson

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import afits as arf
from . import fast_healpix


class SegmentArchiveException(Exception):
    """Exception raised SkyMap error.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Segment archive is corrupted."):
        self.message = message
        super().__init__(self.message)


class SegmentArchive:
    def __init__(self, root):
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
                f"Base NSide of SkyMap must be 32 (EVR) or 256 (Argus), got {nside_base}"
            )

        # NB: The following astropy lookups are used for pixel metadata
        # Actual geometry is done with the fast_healpix subpackage. 
        self.hpix = ahpx.HEALPix(  
            nside=self.nside_base, 
            order='nested', 
            frame=acrd.ICRS(),
        )

        self.subdiv_hpx = []
        for nside in self.subdivs:
            self.subdiv_hpx.append(
                ahpx.HEALPix(nside=nside, order="nested", frame=acrd.ICRS())
            )

        self.fast_healpixer = fast_healpix.FastHealpix()

        self.pixels = self._traverse()

    def _traverse(self):
        n_levels = len(self.subdivs) + 1

        # Traverse the skymap tree, find all full-qualified healpix
        fqhipix = glob.glob(
            os.path.join(self.root, "/".join(["??????"] * n_levels))
        )

        pixels = {}
        for fqi in fqhipix:
            ipix = str(int(fqi.split("/")[-1]))
            pixels[ipix] = {'path': fqi}

        return pixels
    
    def index(self):
        manifest_path = os.path.join(self.root, 'manifest.json')
        summary_path = os.path.join(self.root, 'summary.parquet')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                pixcache = orjson.loads(f.read())
        else:
            pixcache = None

        pix_ids = sorted(list(self.pixels.keys()))
        n_ipix = len(pix_ids)
        with click.progressbar(pix_ids, label='Indexing: ') as pbar:
            for pix in pbar:
                nights = glob.glob(os.path.join(self.pixels[pix]['path'], '????????.fits'))
                    
                self.pixels[pix]['nights'] = {}
                for night in nights:
                    if pixcache is not None and night in pixcache[pix]['nights']:
                        self.pixels[pix]['nights'][night] = pixcache[pix]['nights'][night]
                        continue
                    night_dict = {'ntiles': 0, 'ntiles_zweighted': 0}
                    
                    ahdulist = arf.open(night)
                    tile_size = ahdulist[1].data.size
                    for tile in ahdulist[1:]:
                        night_dict['ntiles'] += 1
                        night_dict['ntiles_zweighted'] += np.count_nonzero(tile.data) / tile_size
                    self.pixels[pix]['nights'][night] = night_dict
        
        for pix in self.pixels:
            total_tiles = 0
            total_tiles_weighted = 0
            for night in self.pixels[pix]['nights']:
                total_tiles += self.pixels[pix]['nights'][night]['ntiles']
                total_tiles_weighted += self.pixels[pix]['nights'][night]['ntiles_zweighted']
            self.pixels[pix]['total_tiles'] = total_tiles
            self.pixels[pix]['total_tiles_weighted'] = total_tiles_weighted

        with open(manifest_path, 'w') as f:
            f.write(orjson.dumps(self.pixels).decode('utf-8'))

        # Finally, write a summary table
        t = np.zeros(n_ipix, dtype=int)
        wt = np.zeros(n_ipix, dtype=np.float32)
        ipix = np.zeros(n_ipix, dtype=int)
        ra = np.zeros(n_ipix, dtype=np.float32)
        dec = np.zeros(n_ipix, dtype=np.float32)
        for i, pix in enumerate(self.pixels):
            t[i] = self.pixels[pix]['total_tiles']
            wt[i] = self.pixels[pix]['total_tiles_weighted']
            ipix[i] = pix
            ra[i], dec[i] = self.fast_healpixer.healpix_to_radec(int(pix), self.nside_base, 0.0, 0.0)

        summary_table = pa.Table.from_pydict(
            {
                'ipix': ipix, 
                'ra': ra, 
                'dec': dec, 
                'n_tiles': t, 
                'n_tiles_density_weighted': wt    
            }
        )
        pq.write_table(summary_table, summary_path)

        return self.pixels

    def get_ipix_path(self, ipix):
        ra, dec = self.fast_healpixer.healpix_to_radec(
            ipix, self.nside_base, 0.0, 0.0,
        )

        path = self.root
        for nside in self.subdivs:
            subhealpix = self.fast_healpixer.radec_to_healpix(ra, dec, nside)

            path = os.path.join(path, f"{subhealpix:06}")
        path = os.path.join(path, f"{ipix:06}")
        return path
    
