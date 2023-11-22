import builtins
import math
from collections import OrderedDict

import blosc
import numpy as np


class ArgusFITSParseError(Exception):
    pass


class ArgusFITSWriteError(Exception):
    pass


class ArgusFITSHeaderError(Exception):
    pass


class ArgusFitsHeader:
    def __init__(self):
        self.keyvals = OrderedDict()
        self.comments = OrderedDict()

    def __getitem__(self, key):
        return self.keyvals[key]

    def __setitem__(self, key, value):
        if type(value) is list and len(value) == 2:
            self.keyvals[key] = value[0]
            self.comments[key] = value[1]
        else:
            self.keyvals[key] = value

    def __iter__(self):
        return iter(self.keyvals)

    def keys(self):
        return self.keyvals.keys()

    def items(self):
        return self.keyvals.items()

    def values(self):
        return self.keyvals.values()

    def from_string(self, header_string):
        # header ends if END is the only thing on one line
        # returns True if we reached the end of the header, False otherwise
        got_header_end = False
        for line_start in range(0, len(header_string), 80):
            line = header_string[line_start : line_start + 80]

            if line.strip() == "END":
                got_header_end = True
                break
            else:
                keyword = line[0:8].strip()
                value = line[11:]
                s = value.split("/")
                value = s[0]
                if len(s) > 1:
                    comment = s[1].strip()
                else:
                    comment = None

                # see if we can convert to a bool or number
                if value.replace("'", "").strip() == "T":
                    value = True
                elif value.replace("'", "").strip() == "F":
                    value = False
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            value = value.replace('"', "").replace("'", "").strip()
                self.keyvals[keyword] = value
                if comment is not None:
                    self.comments[keyword] = value
        return got_header_end

    def update(self, other_header):
        self.keyvals.update(other_header.keyvals)
        self.comments.update(other_header.comments)


class ArgusFitsHDU:
    # only supports image HDUs
    def __init__(self):
        self.data = None
        self.header = ArgusFitsHeader()


class ArgusHDUList:
    def __init__(self, hdus=None):
        self.hdu_list = []

        if type(hdus) is list:
            self.hdu_list = hdus
        if type(hdus) is ArgusFitsHDU:
            self.hdu_list = [hdus]

    def append(self, hdu):
        self.hdu_list.append(hdu)

    def __len__(self):
        return len(self.hdu_list)

    def __repr__(self):
        return self.hdu_list.__repr__()

    def __getitem__(self, n):
        return self.hdu_list[n]

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        self.n += 1
        if self.n < len(self.hdu_list):
            return self.hdu_list[self.n]
        else:
            raise StopIteration

    def writeto(self, filename, overwrite=True):  # noqa: C901
        if not overwrite:
            raise ArgusFITSWriteError("Protecting file write not supported")

        if "XTENSION" in self.hdu_list[0].header:
            raise ArgusFITSWriteError("HDUList does not have a PrimaryHDU")

        with builtins.open(filename, "wb") as outfile:
            for hdu_n, hdu in enumerate(self.hdu_list):
                # write the header first
                if hdu.data is not None:
                    out_array = np.ascontiguousarray(hdu.data.copy())

                    # automatically put the required imaging keywords into the header
                    # and do some other format-dependent setup
                    if hdu.data.dtype == np.int16:
                        hdu.header["BITPIX"] = 16
                        bytes_per_pix = 2
                        out_array = out_array.byteswap()
                    elif hdu.data.dtype == np.uint16:
                        hdu.header["BITPIX"] = 16
                        hdu.header["BZERO"] = 32768
                        hdu.header["BSCALE"] = 1
                        bytes_per_pix = 2
                        out_array = (out_array.astype(np.int32) - 32768.0).astype(
                            np.int16
                        )
                        out_array = out_array.byteswap()
                    elif hdu.data.dtype == np.int32:
                        hdu.header["BITPIX"] = 32
                        bytes_per_pix = 4
                        out_array = out_array.byteswap()
                    elif hdu.data.dtype == np.float16:
                        hdu.header[
                            "SIMPLE"
                        ] = False  # tell readers we're doing something naughty
                        bytes_per_pix = 2
                        hdu.header["BITPIX"] = -16
                    elif hdu.data.dtype == np.float32:
                        bytes_per_pix = 4
                        hdu.header["BITPIX"] = -32
                        out_array = out_array.byteswap()
                    elif hdu.data.dtype == np.float64:
                        bytes_per_pix = 8
                        hdu.header["BITPIX"] = -64
                        out_array = out_array.byteswap()
                    else:
                        raise ArgusFITSWriteError(
                            "Unsupported numpy data type (%s) writing extension %i"
                            % (repr(hdu.data.dtype), hdu_n)
                        )

                    if len(hdu.data.shape) != 2:
                        raise ArgusFITSWriteError(
                            "Only 2D arrays are supported, extension %i has %i dimensions"
                            % (hdu_n, len(hdu.data.shape))
                        )

                    hdu.header["NAXIS"] = 2
                    hdu.header["NAXIS1"] = hdu.data.shape[1]
                    hdu.header["NAXIS2"] = hdu.data.shape[0]
                    hdu.header["PCOUNT"] = 0
                    hdu.header["GCOUNT"] = 1
                else:
                    hdu.header["SIMPLE"] = True
                    hdu.header["BITPIX"] = 8
                    hdu.header["NAXIS"] = 0
                    hdu.header["EXTEND"] = True

                header_string = ""

                # the header is an OrderedDict, so we'll rely on the keywords having been given
                # in the correct FITS order
                for key, value in hdu.header.items():
                    if type(value) is str:
                        val = value
                    elif type(value) is bool:
                        if value:
                            val = "T"
                        else:
                            val = "F"
                    else:
                        val = repr(value)

                    try:
                        comment = hdu.header.comments[key]
                    except KeyError:
                        comment = None

                    if key == "SIMPLE":
                        header_string += "%-80s" % (
                            "%-8s=%21s / conforms to FITS standard" % (key, val)
                        )
                    elif key == "XTENSION":
                        header_string += "%-80s" % ("XTENSION= 'IMAGE   '")

                    else:
                        # get past astropy checks
                        if comment is not None:
                            full_line = "%-8s=%21s / %s" % (key, val, comment)
                        else:
                            full_line = "%-8s=%21s" % (key, val)

                        if len(full_line) > 80:
                            full_line = full_line[:80]

                        header_string += "%-80s" % full_line

                header_string += "%-80s" % "END"

                best_header_size = ((len(header_string) // 2880) + 1) * 2880
                header_format_spec = "%%-%is" % best_header_size
                header_string = header_format_spec % header_string
                header = header_string.encode("utf8")

                outfile.write(header)

                if hdu.data is not None:
                    out_array.tofile(outfile)
                    len_written = hdu.data.shape[0] * hdu.data.shape[1] * bytes_per_pix

                    if len_written % 2880 != 0:
                        # write extra to cope with the FITS file format's chunking
                        extra_length = 2880 - (len_written % 2880)
                        np.zeros(
                            extra_length // bytes_per_pix, dtype=hdu.data.dtype
                        ).tofile(outfile)


def read_blosc_from(file, index, size, dtype=np.float16, compressed=True):
    with builtins.open(file, "rb") as f:
        f.seek(index)
        bytes_read = f.read(size)
        if compressed:
            bytes_read = blosc.decompress(bytes_read)
        data = np.frombuffer(bytes_read, dtype=dtype)
        res = int(math.sqrt(data.size))
        data = data.reshape((res, res))
    return data


def load_hdu_from_file_handle(  # noqa: C901
    file_handle, verbose=False, get_byte_positions=False
):
    # loads from open file until end of HDU,
    # then returns the handle for later seeking
    # requires the file to have been opened in "rb" mode
    got_header_end = False
    hdu = ArgusFitsHDU()
    if verbose:
        print("Loading HDU")

    while not got_header_end:
        header_string = file_handle.read(2880)

        if len(header_string) == 0:
            if get_byte_positions:
                return None, None, None, None
            return None, None

        if len(header_string) < 80:
            raise ArgusFITSParseError("Reached end of file before finishing header")

        header_string = str(header_string, "utf-8")
        if hdu.header.from_string(header_string) is True:
            got_header_end = True

    data_start = file_handle.tell()
    if verbose:
        print("Loaded header:", hdu.header.items())

    # now in image section, if there is one
    if hdu.header["NAXIS"] == 2:
        if "TTYPE1" in hdu.header:
            if hdu.header["TTYPE1"] == "COMPRESSED_DATA":
                raise ArgusFITSParseError(
                    "Image HDUs are compressed, use Astropy instead."
                )
        dtype = None
        byte_swap = True
        if "BLOSC" in hdu.header:
            blosc_data = hdu.header["BLOSC"]
        else:
            blosc_data = False

        if hdu.header["BITPIX"] == 16:
            dtype = np.int16
        if hdu.header["BITPIX"] == 32:
            dtype = np.int32
        if hdu.header["BITPIX"] == -16:
            dtype = np.float16
            byte_swap = False  # since half-float is off the FITS standard anyway...
        if hdu.header["BITPIX"] == -32:
            dtype = np.float32
        if hdu.header["BITPIX"] == -64:
            dtype = np.float64

        if dtype is None:
            raise ArgusFITSParseError(
                f"Unknown datatype {hdu.header['BITPIX']} NAxis: {hdu.header['NAXIS']}"
            )

        n_pixels = hdu.header["NAXIS1"] * hdu.header["NAXIS2"]

        try:
            if blosc_data:
                blosc_bytes = file_handle.read(hdu.header["BLOSCBY"])
                bytes_read = len(blosc_bytes)
                byte_string = blosc.decompress(blosc_bytes)
                hdu.data = np.frombuffer(byte_string, dtype=dtype)
            else:
                hdu.data = np.fromfile(file_handle, dtype=dtype, count=n_pixels)
                bytes_read = (
                    n_pixels * dtype(1).nbytes
                )  # the 1 instantiates an object, required to get attributes
        except ValueError:
            raise ArgusFITSParseError("Error reading image data")

        if verbose:
            print("Loaded", n_pixels, "with a data type of", repr(dtype))
        if byte_swap:
            hdu.data.byteswap(inplace=True)

        if (hdu.header["BITPIX"] > 0) and ("BZERO" in hdu.header):
            if hdu.header["BZERO"] != 0:
                hdu.data += hdu.header["BZERO"]

            if hdu.header["BSCALE"] != 1:
                hdu.data *= hdu.header["BSCALE"]

        hdu.data = hdu.data.reshape(hdu.header["NAXIS2"], hdu.header["NAXIS1"])

        # and read out the alignment blanks so we're in the right place for the next HDU

        if bytes_read % 2880 != 0:
            extra_bytes = 2880 - (bytes_read % 2880)
            file_handle.read(extra_bytes)

    else:
        data_start = 0
        bytes_read = 2880

    if get_byte_positions:
        return file_handle, hdu, data_start, bytes_read
    else:
        return file_handle, hdu


def open(filename, verbose=False, get_byte_positions=False):
    hdulist = ArgusHDUList()

    # need to do it this way to match astropy's module.open() syntax
    with builtins.open(filename, "rb") as file_handle:
        end_of_file = False
        while not end_of_file:
            if get_byte_positions:
                file_handle, hdu, byte_start, nbytes = load_hdu_from_file_handle(
                    file_handle, verbose, get_byte_positions=get_byte_positions
                )
            else:
                file_handle, hdu = load_hdu_from_file_handle(file_handle, verbose)

            if file_handle is not None:
                if get_byte_positions:
                    hdu.header["_BYTE_START"] = byte_start
                    hdu.header["_NBYTES"] = nbytes
                hdulist.append(hdu)
            else:
                end_of_file = True
    return hdulist


if __name__ == "__main__":
    # speed test (verification tests are in test directory)
    import time

    import astropy.io.fits as fits

    argus_hdulist = open("20170308.f32.fits")

    tm = time.perf_counter()
    for n in range(10):
        argus_hdulist = open("20170308.fits")
        for d in argus_hdulist[1:]:
            d.data = d.data.astype(np.float32)
        argus_hdulist.writeto("argus_test.fits", overwrite=True)
    print("Argus: %fs" % (time.perf_counter() - tm))

    tm = time.perf_counter()
    for n in range(10):
        hdulist = fits.open("20170308.fits")
        for d in hdulist[1:]:
            d.data = d.data.astype(np.float32)
        argus_hdulist.writeto("argus_test.fits", overwrite=True)
    print("Argus: %fs" % (time.perf_counter() - tm))

    hdulist = fits.HDUList(fits.PrimaryHDU())
    for dtype in [np.float32, np.float64, np.int16, np.int32, np.uint16]:
        test_array = np.ones((10, 10), dtype=dtype) * 1000
        hdulist.append(fits.ImageHDU(test_array))
        hdulist[-1].header["DTYPE"] = dtype.__name__
    hdulist.writeto("test_dtypes.fits", overwrite=True)

    argus_hdulist = open("test_dtypes.fits")
    print("Argus loaded values (should all be 1000 or 1000.0)")
    for hdu in argus_hdulist:
        print("\t", hdu.header["DTYPE"], hdu.data[0, 0])
    argus_hdulist.writeto("test_dtypes_argus.fits")

    # and load it back in
    print("Argus written values as loaded by astropy")
    argus_hdulist = fits.open("test_dtypes.fits")  # this does complete FITS parsing, so
    # tests both header & image parsing
    for hdu in argus_hdulist[1:]:
        print("\t", hdu.header["DTYPE"], hdu.data[0, 0])
