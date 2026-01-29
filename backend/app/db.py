from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import pymysql

from .config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @contextmanager
    def connect(self) -> Generator[pymysql.connections.Connection, None, None]:
        conn = pymysql.connect(
            host=self._settings.db_host,
            port=self._settings.db_port,
            user=self._settings.db_user,
            password=self._settings.db_pass,
            database=self._settings.db_name,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()

