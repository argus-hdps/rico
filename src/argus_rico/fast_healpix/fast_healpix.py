import sys

import cffi
import numpy as np

from .fast_healpix_c import lib as fast_healpix_mod  # noqa: E402


class FastHealpix:
    def __init__(self, recompile=False, max_call_len=10000):
        # compile the C code and import the module
        self.ffi = cffi.FFI()

        self.max_call_len = max_call_len

        self.ras = np.zeros(max_call_len, dtype=np.float64)
        self.decs = np.zeros(max_call_len, dtype=np.float64)
        self.healpixes = np.zeros(max_call_len, dtype=np.int64)
        self.ra_ret = self.ffi.cast("double *", self.ras.ctypes.data)
        self.dec_ret = self.ffi.cast("double *", self.decs.ctypes.data)
        self.healpixes_ret = self.ffi.cast("long int *", self.healpixes.ctypes.data)

    def healpixes_to_radec(self, healpixes, nside, dx, dy):
        npix = len(healpixes)
        if npix > self.max_call_len:
            print("Exceeded maximum list length in healpixes_to_radec")
            sys.exit(1)

        healpixes = np.array(healpixes, dtype=np.int64)
        healpixes_c = self.ffi.cast("long int *", healpixes.ctypes.data)

        fast_healpix_mod.healpixls_to_radecdeg(
            healpixes_c, npix, nside, dx, dy, self.ra_ret, self.dec_ret
        )

        return self.ras[:npix], self.decs[:npix]

    def healpix_deltagrid_to_radec(self, healpix, nside, dxs, dys):
        npoints = len(dxs)
        if npoints > self.max_call_len:
            print("Exceeded maximum list length in healpixes_to_radec")
            sys.exit(1)

        dxs = np.array(dxs, dtype=np.float64)
        dys = np.array(dys, dtype=np.float64)
        dxs_c = self.ffi.cast("double *", dxs.ctypes.data)
        dys_c = self.ffi.cast("double *", dys.ctypes.data)

        fast_healpix_mod.healpixl_grid_to_radecdeg(
            healpix, npoints, nside, dxs_c, dys_c, self.ra_ret, self.dec_ret
        )

        return self.ras[:npoints], self.decs[:npoints]

    def healpix_to_radec(self, healpix, nside, dx, dy):
        fast_healpix_mod.healpixl_to_radecdeg(
            healpix, nside, dx, dy, self.ra_ret, self.dec_ret
        )

        return self.ras[0], self.decs[0]

    def radec_to_healpix(self, ra, dec, nside):
        return fast_healpix_mod.radec_to_healpixl(ra, dec, nside)

    def radecs_to_healpixes(self, ras, decs, nside):
        nras = len(ras)
        if nras > self.max_call_len:
            print("Exceeded maximum list length in radecs_to_healpixes")
            sys.exit(1)

        ras = np.array(ras, dtype=np.float64)
        decs = np.array(decs, dtype=np.float64)
        ras_c = self.ffi.cast("double *", ras.ctypes.data)
        decs_c = self.ffi.cast("double *", decs.ctypes.data)

        fast_healpix_mod.radecs_to_healpixls(
            ras_c, decs_c, nras, self.healpixes_ret, nside
        )

        return self.healpixes[:nras]
