import base64
from typing import List, Type, TypeVar

import blosc
import numpy as np
import orjson
from pydantic import BaseModel

EFTEAlertType = TypeVar("EFTEAlertType", bound="EFTEAlert")


class EFTECandidate(BaseModel):
    stamp_bytes: bytes
    epoch: float
    camera: str
    thresh: float
    vetnet_score: float
    npix: int
    tnpix: int
    xmin: int
    xmax: int
    ymin: int
    ymax: int
    xcentroid: float
    ycentroid: float
    x2: float
    y2: float
    xy: float
    errx2: float
    erry2: float
    errxy: float
    a: float
    b: float
    theta: float
    cxx: float
    cyy: float
    cxy: float
    cflux: float
    flux: float
    cpeak: float
    peak: float
    xcpeak: int
    ycpeak: int
    xpeak: int
    ypeak: int
    flag: int
    aper_sum_bkgsub: float
    annulus_rms: float
    difsnr: float
    hfd: float
    sign_ratio: float
    insmag: float
    zpoint: float
    gmag: float
    srcsnr: float
    ra: float
    dec: float

    @property
    def stamp(self):
        return (
            np.frombuffer(
                blosc.decompress(
                    base64.b64decode(
                        self.stamp_bytes,
                    )
                ),
                dtype=np.float32,
            )
            .reshape((30, 30, 3))
            .byteswap()
        )


# Create a Pydantic model for the 'xmatch' list of dictionaries
class XMatchItem(BaseModel):
    ra: float
    dec: float
    parallax: float
    pmra: float
    pmdec: float
    g: float
    r: float
    i: float
    separation: float


class EFTEAlert(BaseModel):
    schemavsn: str
    publisher: str
    objectId: str
    candidate: EFTECandidate
    xmatch: List[XMatchItem]

    @classmethod
    def from_json(cls: Type[EFTEAlertType], json_path: str) -> EFTEAlertType:
        with open(json_path, "rb") as f:
            alert = orjson.loads(f.read())
        return cls(**alert)
