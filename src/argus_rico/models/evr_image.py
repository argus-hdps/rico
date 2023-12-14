import datetime
import os
import socket
import uuid
import warnings
from typing import Any, Dict, Optional, Type, TypeVar, Union

import astropy.io.fits as fits
import astropy.units as u
import astropy.wcs as awcs
import astropy_healpix as ahpx
import numpy as np
from geojson_pydantic import Polygon
from pydantic import BaseModel, Field, ValidationError

warnings.simplefilter("ignore", category=awcs.FITSFixedWarning)


# Q = qlsc.QLSC(depth=30)
H = ahpx.HEALPix(nside=2**24, order="nested")
HOSTNAME = socket.gethostname()


EVRImageType = TypeVar("EVRImageType", bound="EVRImage")
EVRImageUpdateType = TypeVar("EVRImageUpdateType", bound="EVRImageUpdate")


def _wcs_to_footprint(header: fits.Header) -> Dict[str, Any]:
    """
     Converts the WCS header information to a GeoJSON polygon footprint.

    Args:
        header: FITS header containing WCS information.

    Returns:
        Dictionary representing the GeoJSON polygon footprint.

    """
    w = awcs.WCS(header)
    im_center = w.all_pix2world(3288, 2192, 0)
    header["CRVAL1"] = float(im_center[0])
    header["CRVAL2"] = float(im_center[1])

    x = np.arange(0, 6575, 274)
    y = np.arange(0, 4384, 274)

    bottom_edge = list(zip([0] * len(x), x)) + [(0, 6575)]
    right_edge = list(zip(y, [6575] * len(y)))[1:] + [(4383, 6575)]
    top_edge = list(zip([4383] * len(x), x)) + [(4383, 6575)]
    top_edge = list(reversed(top_edge))[1:]
    left_edge = list(zip(y, [0] * len(y))) + [(4383, 0)]
    left_edge = list(reversed(left_edge))[1:]

    poly = np.array(bottom_edge + right_edge + top_edge + left_edge)
    poly = np.array([poly.T[1], poly.T[0]]).T

    radecs = w.all_pix2world(poly, 0)
    # Re-orient RA from [-180,180]
    radecs[:, 0] -= 180
    radecs = [list(r) for r in radecs]

    footprint = {"type": "Polygon", "coordinates": [radecs]}
    return footprint


def fitspath_to_constructor(fitspath: Union[str, fits.HDUList]) -> Dict[str, Any]:
    """
    Convert a FITS header into a Pydantic constructor dictionary.

    Args:
        fitspath (str or astropy.io.fits.HDUList): The path to the FITS file or
        and HDUList object.

    Returns:
        Dict[str, Any]: The Pydantic constructor dictionary representing the FITS header.

    Raises:
        KeyError: If any required FITS header fields are missing.
    """
    if type(fitspath) is str:
        hdulist = fits.open(fitspath)

    if len(hdulist) == 1:
        hdu_num = 0
    else:
        hdu_num = 1
    header = hdulist[hdu_num].header.copy()
    hdulist.close()

    if "FIELDID" not in header:
        header["FIELDID"] = 400

    constructor_dict = {}
    constructor_dict["camera"] = header["CCDDETID"]
    constructor_dict["filter_name"] = header["FILTER"]
    constructor_dict["image_type"] = header["IMGTYPE"].strip()
    constructor_dict["obstime"] = header["DATE-OBS"] + "T" + header["TIME-OBS"]
    if "GPSTIME" in header and "Z" in header["GPSTIME"]:
        constructor_dict["gpstime"] = header["GPSTIME"]
    constructor_dict["ccd_set_temp"] = header["SETTEMP"]
    constructor_dict["ccd_temp"] = header["CCDTEMP"]
    constructor_dict["exp_time"] = header["EXPTIME"]
    constructor_dict["site_name"] = header["TELOBS"]
    constructor_dict["server_name"] = HOSTNAME
    constructor_dict["basename"] = header["ORIGNAME"].split(".")[0]
    constructor_dict["fieldid"] = header["FIELDID"]
    constructor_dict["ratchnum"] = header["RATCHNUM"]
    constructor_dict["mount_ha"] = header["MOUNTHA"]
    constructor_dict["sha1"] = header["CHECKSUM"]
    constructor_dict["ccd_ext_temp"] = header["CCDETEMP"]
    constructor_dict["wind_dir"] = header["WINDDIR"]
    constructor_dict["wind_speed"] = header["WINDSPED"]
    constructor_dict["rel_humidity"] = header["OUTRELHU"]
    constructor_dict["dew_point"] = header["OUTDEWPT"]
    constructor_dict["air_pressure"] = header["OUTPRESS"]
    constructor_dict["mushroom_temp"] = header["INR1TEMP"]
    constructor_dict["inc_x"] = header["INR1INCX"]
    constructor_dict["inc_y"] = header["INR1INCY"]
    constructor_dict["inc_z"] = header["INR1INCZ"]

    if "CRVAL1" in header:
        constructor_dict["hid"] = H.lonlat_to_healpix(
            header["CRVAL1"] * u.deg, header["CRVAL2"] * u.deg
        )

        constructor_dict["footprint"] = Polygon(**_wcs_to_footprint(header))
        constructor_dict["wcspath"] = os.path.abspath(fitspath)
    else:
        constructor_dict["rawpath"] = os.path.abspath(fitspath)
    return constructor_dict


class EVRImage(BaseModel):
    """Class representing an EVR image."""

    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    camera: Optional[str] = Field(...)
    filter_name: str = Field(...)
    obstime: datetime.datetime = Field(...)
    gpstime: Optional[datetime.datetime] = None
    ccd_set_temp: float = Field(...)
    ccd_temp: float = Field(...)
    exp_time: float = Field(...)

    site_name: str = Field(...)
    server_name: str = Field(...)
    image_type: str = Field(...)
    rawpath: Optional[str] = None
    wcspath: Optional[str] = None
    basename: str = Field(...)
    fieldid: float = Field(...)
    ratchnum: str = Field(...)
    mount_ha: Optional[float] = Field(...)
    sha1: str = Field(...)
    ccd_ext_temp: float = Field(...)
    wind_dir: float = Field(...)
    wind_speed: float = Field(...)
    rel_humidity: float = Field(...)
    dew_point: float = Field(...)
    air_pressure: float = Field(...)
    mushroom_temp: float = Field(...)
    inc_x: Optional[float] = Field(...)
    inc_y: Optional[float] = Field(...)
    inc_z: Optional[float] = Field(...)

    footprint: Optional[Polygon] = Field(...)
    hid: Optional[int] = Field(...)

    class Config:
        """Pydantic configuration."""

        allow_population_by_field_name = True

    @classmethod
    def from_fits(cls: Type[EVRImageType], fitspath: str) -> EVRImageType:
        """Create an instance of EVRImage from a FITS file.

        Args:
            fitspath: Path to the FITS file.

        Returns:
            An instance of EVRImage.

        """

        constructor_dict = fitspath_to_constructor(fitspath)

        # This is duplicated boiler plate between the Image/ImageUpdate classes
        try:
            inst = cls(**constructor_dict)
        except ValidationError as e:
            for error in e.errors():
                field = error["loc"][0]
                constructor_dict[field] = None
            inst = cls(**constructor_dict)

        return inst


class EVRImageUpdate(BaseModel):
    """Class representing an update to an EVR image."""

    camera: Optional[str]
    filter_name: Optional[str]
    obstime: Optional[datetime.datetime]
    gpstime: Optional[datetime.datetime]
    ccd_set_temp: Optional[float]
    ccd_temp: Optional[float]
    exp_time: Optional[float]
    site_name: Optional[str]
    server_name: Optional[str]
    image_type: Optional[str]
    rawpath: Optional[str]
    wcspath: Optional[str]
    basename: Optional[str]
    fieldid: Optional[float]
    ratchnum: Optional[str]
    sha1: Optional[str]
    ccd_ext_temp: Optional[float]
    wind_dir: Optional[float]
    wind_speed: Optional[float]
    rel_humidity: Optional[float]
    dew_point: Optional[float]
    air_pressure: Optional[float]
    mushroom_temp: Optional[float]
    inc_x: Optional[float]
    inc_y: Optional[float]
    inc_z: Optional[float]
    footprint: Optional[Polygon]
    hid: Optional[int]

    class Config:
        """Pydantic configuration."""

        allow_population_by_field_name = True

    @classmethod
    def from_fits(cls: Type[EVRImageUpdateType], fitspath: str) -> EVRImageUpdateType:
        """Create an instance of EVRImageUpdate from a FITS file.

        Args:
            fitspath: Path to the FITS file.

        Returns:
            An instance of EVRImageUpdate.

        """
        constructor_dict = fitspath_to_constructor(fitspath)

        # This is duplicated boiler plate between the Image/ImageUpdate classes
        try:
            inst = cls(**constructor_dict)
        except ValidationError as e:
            for error in e.errors():
                field = error["loc"][0]
                constructor_dict[field] = None
            inst = cls(**constructor_dict)

        return inst
