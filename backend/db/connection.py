"""DuckDB connection provider and thread-safe execution manager.

Authoritative reference: docs/backend/backend-architecture.md
DuckDB opens one connection per process; thread-safe execution lock is used for writes.
"""

from contextlib import contextmanager
import threading
from typing import Generator, Optional
import duckdb
from backend.config import settings
from backend.db.migrations import run_migrations
from backend.utils.errors import DatabaseUnavailableError
from backend.utils.logging import logger


_connection: Optional[duckdb.DuckDBPyConnection] = None
_lock = threading.RLock()


def init_db(database_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """Initialize DuckDB connection, run migrations, and store global reference."""
    global _connection
    with _lock:
        target_path = database_path or settings.DB_PATH
        settings.ensure_directories()
        conn: Optional[duckdb.DuckDBPyConnection] = None
        try:
            conn = duckdb.connect(database=target_path)
            run_migrations(conn)
            _connection = conn
            logger.info(f"Connected to DuckDB database at: {target_path}")
            return _connection
        except Exception as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            _connection = None
            logger.error(f"Failed to initialize DuckDB at {target_path}: {exc}")
            raise DatabaseUnavailableError(f"Cannot access DuckDB at {target_path}: {exc}") from exc


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Get the active DuckDB connection, initializing if not already open."""
    global _connection
    with _lock:
        if _connection is None:
            return init_db()
        return _connection


def close_db() -> None:
    """Close active DuckDB connection."""
    global _connection
    with _lock:
        if _connection is not None:
            try:
                _connection.close()
                logger.info("DuckDB connection closed cleanly.")
            except Exception as e:
                logger.warning(f"Error while closing DuckDB: {e}")
            finally:
                _connection = None


def get_db_lock() -> threading.RLock:
    """Return the re-entrant lock used for DuckDB write operations."""
    return _lock


@contextmanager
def db_cursor() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager yielding the active connection under thread lock."""
    conn = get_db_connection()
    with _lock:
        yield conn


@contextmanager
def db_transaction() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager executing a block inside a transaction with thread locking."""
    conn = get_db_connection()
    with _lock:
        conn.begin()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
