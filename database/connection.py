
import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg import Connection

load_dotenv()


def get_database_config() -> dict[str, str | int]:
    """Load PostgreSQL configuration from environment variables."""

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable, "").strip()
    ]

    if missing_variables:
        raise RuntimeError(
            "Missing database configuration: "
            + ", ".join(missing_variables)
        )

    return {
        "host": os.environ["DB_HOST"].strip(),
        "port": int(os.environ["DB_PORT"]),
        "dbname": os.environ["DB_NAME"].strip(),
        "user": os.environ["DB_USER"].strip(),
        "password": os.environ["DB_PASSWORD"],
    }


def get_connection() -> Connection:
    """Create and return a PostgreSQL connection."""

    config = get_database_config()

    return psycopg.connect(
        **config,
        connect_timeout=10,
    )


@contextmanager
def get_db_connection() -> Iterator[Connection]:
    """
    Provide a database connection with automatic cleanup.

    Commits on success and rolls back if an exception occurs.
    """

    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
