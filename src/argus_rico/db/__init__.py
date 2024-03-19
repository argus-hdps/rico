__all__ = ["RicoDBSessionManager", "RicoDBConnectionManager"]

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .. import config


class RicoDBConnectionManager:
    def __enter__(self):
        db_url_escaped = f"postgresql+psycopg://{config.HDPS_DB_USER}:{quote_plus(config.HDPS_DB_PASS)}@{config.HDPS_DB_ADDR}:{config.HDPS_DB_PORT}".replace(
            "%", "%%"
        )
        self.engine = create_engine(db_url_escaped)
        self.conn = self.engine.connect()
        return self.conn

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.conn.close()


class RicoDBSessionManager:
    def __enter__(self):
        db_url_escaped = f"postgresql+psycopg://{config.HDPS_DB_USER}:{quote_plus(config.HDPS_DB_PASS)}@{config.HDPS_DB_ADDR}:{config.HDPS_DB_PORT}".replace(
            "%", "%%"
        )
        self.engine = create_engine(db_url_escaped)
        self.sess = Session(self.engine)
        return self.sess

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.sess.close()
