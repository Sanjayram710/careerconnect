import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SQLITE_DB_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "placement.db"
)

# Fetch PostgreSQL URL
raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url and raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

POSTGRES_URL = raw_db_url or "postgresql://postgres:postgres@localhost:5432/placement_portal"


def migrate_data():
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database file not found at: {SQLITE_DB_PATH}")
        return

    logger.info("Connecting to SQLite database...")
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    logger.info("Connecting to PostgreSQL database...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_URL)
        pg_conn.autocommit = False
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        sqlite_conn.close()
        return

    # List of tables to migrate in order of dependency
    # Format: (sqlite_table_name, postgres_table_name)
    tables = [
        ("students", "students"),
        ("jobs", "jobs"),
        ("live_jobs", "live_jobs"),
        ("live_internship", "live_internship"),
        ("applications", "applications"),
        ("messages", "messages"),
        ("saved_jobs", "saved_jobs"),
        ("saved_internships", "saved_internships"),
        ("company_news_cache", "company_news_cache"),
        ("bookmarked_news", "bookmarked_news"),
        ("tracked_applications", "tracked_applications"),
        ("placement_events", "placement_events"),
        ("sync_logs", "sync_logs")
    ]

    try:
        # Check tables in SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        sqlite_existing_tables = {row[0] for row in sqlite_cursor.fetchall()}
        logger.info(f"Existing SQLite tables: {sqlite_existing_tables}")

        # Check tables in PostgreSQL
        pg_cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )
        pg_existing_tables = {row[0] for row in pg_cursor.fetchall()}
        logger.info(f"Existing PostgreSQL tables: {pg_existing_tables}")

        for sqlite_table, pg_table in tables:
            if sqlite_table not in sqlite_existing_tables:
                logger.warning(f"Table '{sqlite_table}' does not exist in SQLite placement.db. Skipping...")
                continue
            if pg_table not in pg_existing_tables:
                logger.warning(f"Table '{pg_table}' does not exist in PostgreSQL. Checking if schema needs creation...")
                continue

            logger.info(f"Migrating table {sqlite_table} -> {pg_table}...")

            # Clean PostgreSQL table first to prevent duplicate key errors
            pg_cursor.execute(f"TRUNCATE TABLE {pg_table} RESTART IDENTITY CASCADE;")

            # Fetch columns and data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {sqlite_table};")
            rows = sqlite_cursor.fetchall()
            if not rows:
                logger.info(f"No records found in SQLite table '{sqlite_table}'.")
                continue

            columns = rows[0].keys()
            
            # Prepare SQL insertion query
            col_list = ", ".join([f'"{c}"' for c in columns])
            placeholder_list = ", ".join(["%s"] * len(columns))
            insert_query = f"INSERT INTO {pg_table} ({col_list}) VALUES ({placeholder_list});"

            # Execute insertions
            records_count = 0
            for row in rows:
                values = []
                for col in columns:
                    val = row[col]
                    # Handle data conversion issues (e.g. string representation of boolean or date)
                    if isinstance(val, str) and (val.lower() == 'true' or val.lower() == 'false'):
                        val = val.lower() == 'true'
                    values.append(val)

                pg_cursor.execute(insert_query, tuple(values))
                records_count += 1

            logger.info(f"Successfully migrated {records_count} records to {pg_table}.")

            # Reset the serial sequence to max id to prevent key collision issues
            try:
                seq_query = f"SELECT setval(pg_get_serial_sequence('{pg_table}', 'id'), coalesce(max(id), 1), max(id) IS NOT NULL) FROM {pg_table};"
                pg_cursor.execute(seq_query)
            except Exception as seq_err:
                # Some tables may not have an 'id' column or a sequence (e.g. custom schemas without serial)
                logger.warning(f"Could not reset sequence for table '{pg_table}': {seq_err}")
                pg_conn.commit()  # commit after warning to keep moving

        # Commit everything to PostgreSQL
        pg_conn.commit()
        logger.info("Database migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration error encountered: {e}")
        logger.info("Rolling back PostgreSQL changes...")
        pg_conn.rollback()
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate_data()
