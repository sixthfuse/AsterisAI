import os

import psycopg
from dotenv import load_dotenv

from production_config import SETTINGS

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=SETTINGS.database_connect_timeout_seconds,
        application_name="asteris-api",
    )


def database_ready() -> bool:
    """Perform a bounded read-only readiness probe."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except psycopg.Error:
        return False
