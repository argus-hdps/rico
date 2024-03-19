from datetime import datetime
from typing import Union

import pandas as pd
from astropy.time import Time
from sqlalchemy import and_

from .. import RicoDBSessionManager


class TimeSeriesMixin:
    @classmethod
    def range_to_dataframe(
        cls, t0: Union[datetime, Time, str], t1: Union[datetime, Time, str]
    ) -> pd.DataFrame:

        if isinstance(t0, Time):
            t0 = t0.to_datetime()
        elif isinstance(t0, str):
            t0 = datetime.fromisoformat(t0)

        if isinstance(t1, Time):
            t1 = t1.to_datetime()
        elif isinstance(t1, str):
            t1 = datetime.fromisoformat(t1)

        with RicoDBSessionManager() as sess:
            query = sess.query(cls).filter(and_(cls.epoch >= t0, cls.epoch <= t1))
            df = pd.read_sql(query.statement, sess.bind)
        return df
