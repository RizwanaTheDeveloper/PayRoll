import os
import psycopg
from psycopg.rows import namedtuple_row
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set"
        )

    return psycopg.connect(
        database_url,
        row_factory=namedtuple_row
    )