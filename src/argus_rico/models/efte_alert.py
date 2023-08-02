import base64
from typing import List

import blosc
from pydantic import BaseModel


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
        return blosc.decompress(base64.b64decode(self.stamp_bytes))


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
