__all__ = ["FastHealpix", "fast_healpix_mod"]
import os

try:
    from .fast_healpix import FastHealpix
    from .fast_healpix_c import lib as fast_healpix_mod

except ModuleNotFoundError:
    import distutils.sysconfig

    import cffi

    c_library_name = f"fast_healpix_c"

    c_function_defs = r"""
    void healpixls_to_radecdeg(long int *ihp, int n_hpxes, int Nside, double dx, double dy, double* ra, double* dec);
    void healpixl_to_radecdeg(long int hp, int Nside, double dx, double dy, double* ra, double* dec);
    void healpixl_grid_to_radecdeg(long int hp, int n_points, int Nside, double *dx, double *dy, double* ra, double* dec);
    long int radec_to_healpixl(double ra, double dec, int Nside);
    void radecs_to_healpixls(double *ra, double *dec, int n_points, long int *hpixes, int Nside);
    """

    # compile the C code and import the module
    ffi = cffi.FFI()
    ffi.set_source(
        c_library_name,
        open(f"{os.path.dirname(__file__)}/fast_healpix_c_code.c", "r").read(),
        extra_compile_args=["-O3", "-msse2", "-std=c99"],
    )
    ffi.cdef(c_function_defs)
    ffi.compile(
        verbose=True,
        target=f"{os.path.dirname(__file__)}/fast_healpix_c{distutils.sysconfig.get_config_var('EXT_SUFFIX')}",
        tmpdir=f"{os.path.dirname(__file__)}/",
    )

    from .fast_healpix import FastHealpix
    from .fast_healpix_c import lib as fast_healpix_mod
