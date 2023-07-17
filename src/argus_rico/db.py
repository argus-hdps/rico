__all__ = ["insert_efte_candidates"]

import datetime
import os

import astropy.table as tbl
import astropy.time as atime
import astropy.visualization as viz
import numpy as np
import psycopg
import skimage as sk

from . import config, get_logger

log = get_logger("__name__")


def insert_efte_candidates(catalog):
    if len(catalog) == 0:
        return False

    conn = psycopg.connect(
        f"""host='{config.EFTE_DB_ADDR}'
            port='{config.EFTE_DB_PORT}'
            dbname='{config.EFTE_DB_NAME}'
            user='{config.EFTE_DB_USER}'
            password='{config.EFTE_DB_PASS}'
        """,
        # cursor_factory=psycopg.ClientCursor,
    )

    c = conn.cursor()

    now = datetime.datetime.utcnow()
    imgepoch = atime.Time(catalog.meta["EPOCH"], format="isot", scale="utc")
    epoch = [imgepoch.to_datetime()] * len(catalog)
    lag = [np.abs((now - imgepoch.to_datetime()).total_seconds())] * len(catalog)
    camera = [catalog.meta["CCD"]] * len(catalog)
    ratchet = [catalog.meta["ratchetnum"]] * len(catalog)
    filename = [catalog.meta["FILENAME"]] * len(catalog)

    zed = viz.ZScaleInterval()
    stamps = [
        sk.img_as_ubyte(zed(x)).astype(np.uint8).tobytes()
        for x in catalog["stamp"].data
    ]
    if "bstamps" not in catalog.colnames:
        catalog.add_column(tbl.Column(stamps, name="bstamps"))

    ra = catalog["ra"].data.astype(float)
    dec = catalog["dec"].data.astype(float)
    x = catalog["xcentroid"].data.astype(float)
    y = catalog["ycentroid"].data.astype(float)
    sign_ratio = catalog["sign_ratio"].data.astype(float)
    srcsnr = catalog["srcsnr"].data.astype(float)
    gmag = catalog["gmag"].data.astype(float)
    difsnr = catalog["difsnr"].data.astype(float)
    vetscore = catalog["vetnet"].data.astype(float)
    stamps = catalog["bstamps"].data
    site = ["mlo"] * len(stamps)

    rows = tuple(zip(epoch, stamps))

    try:
        q = """
               INSERT INTO stamps (epoch, cutout)
               VALUES (%s, %s)
               RETURNING id"""
        c.executemany(q, rows, returning=True)
        stamp_ids = []
        while True:
            stamp_ids.append(c.fetchone()[0])
            if not c.nextset():
                break

    except Exception as e:
        log.error(
            "Stamp insert failed for {}  aborting: {} {}".format(
                os.path.basename(catalog.meta["FILENAME"]), q, e
            )
        )

        c.close()
        conn.close()
        return False

    rows = list(
        zip(
            epoch,
            ra,
            dec,
            x,
            y,
            sign_ratio,
            vetscore,
            srcsnr,
            difsnr,
            gmag,
            camera,
            ratchet,
            filename,
            lag,
            site,
            stamp_ids,
        )
    )

    q = """
            INSERT INTO  candidates(
                               epoch,
                               raj2000,
                               decj2000,
                               x_position,
                               y_position,
                               sign_ratio,
                               vetnet_score,
                               srcsnr,
                               difsnr,
                               mag_g,
                               camera,
                               ratchet,
                               detection_image,
                               detection_lag,
                               detected_from,
                               stamp_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
    c.executemany(q, rows)

    c.close()
    conn.commit()
    conn.close()
