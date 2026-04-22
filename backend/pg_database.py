from contextlib import contextmanager
from typing import Optional

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

try:
    from .config import settings
except ImportError:
    from config import settings


class PostgresManager:
    def __init__(self) -> None:
        self._pool: Optional[pool.SimpleConnectionPool] = None

    def connect(self) -> None:
        if self._pool is None:
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=settings.psycopg2_dsn,
            )

    def close(self) -> None:
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None

    @contextmanager
    def get_connection(self):
        if self._pool is None:
            self.connect()

        assert self._pool is not None
        connection = self._pool.getconn()
        try:
            yield connection
        finally:
            self._pool.putconn(connection)

    @contextmanager
    def get_cursor(self):
        with self.get_connection() as connection:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            try:
                yield connection, cursor
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()


db_manager = PostgresManager()


def initialize_tables() -> None:
    create_violations_table = """
    CREATE TABLE IF NOT EXISTS violations (
        id SERIAL PRIMARY KEY,
        type VARCHAR(50) NOT NULL,
        plate VARCHAR(20) NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        confidence DOUBLE PRECISION NOT NULL,
        image_url TEXT,
        location VARCHAR(255)
    );
    """

    create_vehicles_table = """
    CREATE TABLE IF NOT EXISTS vehicles (
        id SERIAL PRIMARY KEY,
        plate VARCHAR(20) UNIQUE NOT NULL,
        owner_name VARCHAR(100) NOT NULL,
        phone VARCHAR(20) NOT NULL
    );
    """

    create_stolen_vehicles_table = """
    CREATE TABLE IF NOT EXISTS stolen_vehicles (
        id SERIAL PRIMARY KEY,
        plate VARCHAR(20) UNIQUE NOT NULL
    );
    """

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(create_violations_table)
        cursor.execute(create_vehicles_table)
        cursor.execute(create_stolen_vehicles_table)
