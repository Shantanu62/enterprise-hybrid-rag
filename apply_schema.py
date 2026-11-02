
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

schema_path = Path(__file__).parent / "database" / "schema.sql"

try:
    if not schema_path.exists():
        raise FileNotFoundError("database/schema.sql not found.")

    schema_sql = schema_path.read_text(encoding="utf-8")

    with psycopg.connect(
        **DB_CONFIG,
        connect_timeout=10,
        autocommit=True,
    ) as conn:
        conn.execute(schema_sql, prepare=False)

    print("SUCCESS: Database schema applied.")

except Exception as error:
    print("FAILED: Database schema was not applied.")
    print("Error type:", type(error).__name__)
    print("Error:", str(error))
