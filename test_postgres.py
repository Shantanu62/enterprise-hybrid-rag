
import os
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

try:
    with psycopg.connect(**DB_CONFIG, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_database(), current_user, version();"
            )
            result = cur.fetchone()

            print("PostgreSQL connection successful!")
            print("Database:", result[0])
            print("User:", result[1])
            print("Version:", result[2].split(",")[0])

except Exception as error:
    print("PostgreSQL connection failed.")
    print("Error type:", type(error).__name__)
    print("Please check your .env configuration.")
