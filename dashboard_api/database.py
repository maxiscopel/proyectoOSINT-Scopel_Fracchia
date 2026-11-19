"""Conexion a PostgreSQL (osint-postgres) con las variables de entorno del proyecto."""
import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _dsn() -> str:
    user = os.environ["POSTGRES_USER"]
    pwd = os.environ["POSTGRES_PASSWORD"]
    name = os.environ["POSTGRES_DB"]
    host = os.environ.get("POSTGRES_HOST", "osint-postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"host={host} port={port} dbname={name} user={user} password={pwd}"


pool = ConnectionPool(_dsn(), min_size=1, max_size=5, open=False,
                      kwargs={"row_factory": dict_row})


def open_pool() -> None:
    pool.open(wait=True, timeout=30)


def close_pool() -> None:
    pool.close()
