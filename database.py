import os
import psycopg
from psycopg.rows import namedtuple_row


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    return psycopg.connect(
        database_url,
        row_factory=namedtuple_row
    )