from pathlib import Path
import sqlite3
import pandas as pd
import time
from typing import Optional

# Resolve path from this file: src/sequalizer/database.py -> project root -> data/
# We need three .parent steps: sequalizer -> src -> project root.
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "Chinook_Sqlite.sqlite"


class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass


class DatabaseManager:
    def __init__(self, timeout: float = 10.0) -> None:
        # Fail fast with a clear message if the DB file is missing. sqlite3.connect()
        # would create an empty DB if the path is writable; we want the existing file.
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database file not found: {DB_PATH}")
        
        try:
            self.conn = sqlite3.connect(DB_PATH, timeout=timeout)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            self.cursor = self.conn.cursor()
        except sqlite3.OperationalError as e:
            raise DatabaseError(f"Failed to connect to database: {e}") from e

    def _handle_operational_error(self, error: sqlite3.OperationalError) -> None:
        """Handle OperationalError exceptions with specific error messages"""
        error_msg = str(error).lower()
        
        if "locked" in error_msg:
            raise DatabaseError("Database is locked. Please try again later.") from error
        elif "no such table" in error_msg:
            raise DatabaseError(f"Table not found: {error}") from error
        elif "syntax error" in error_msg:
            raise DatabaseError(f"SQL syntax error: {error}") from error
        elif "unable to open database" in error_msg:
            raise DatabaseError(f"Unable to open database: {error}") from error
        elif "readonly database" in error_msg:
            raise DatabaseError("Database is in read-only mode.") from error
        else:
            raise DatabaseError(f"Database operation failed: {error}") from error

    def _execute_with_retry(self, query: str, max_retries: int = 5) -> sqlite3.Cursor:
        """Execute query with retry logic for locked database scenarios"""
        for attempt in range(max_retries):
            try:
                cursor = self.conn.cursor()
                cursor.execute(query)
                return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff: wait 0.1s, 0.2s, 0.4s, 0.8s...
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                else:
                    self._handle_operational_error(e)
            except sqlite3.Error as e:
                query_preview = query.strip().split("\n")[0][:80]
                raise DatabaseError(f"Query failed ({query_preview!r}...): {e}") from e


    def execute_query(self, query: str) -> tuple[list[str], list[tuple]]:
        """Execute a SELECT query and return column descriptions and results"""
        try:
            cursor = self._execute_with_retry(query)
            
            # cursor.description is None for non-SELECT queries
            if cursor.description is None:
                return [], []
            
            return cursor.description, cursor.fetchall()
        except DatabaseError:
            # Re-raise DatabaseError as-is
            raise
        except Exception as e:
            # Catch any unexpected errors
            query_preview = query.strip().split("\n")[0][:80]
            raise DatabaseError(f"Unexpected error executing query ({query_preview!r}...): {e}") from e

    def __enter__(self):
        return self

    # Context manager protocol: __exit__ receives (exc_type, exc_val, exc_tb) when the
    # with-block ends. We must accept them even if unused. We always close the connection
    # so it's released even when the with-block raises; then we return None so the
    # exception continues to propagate to the caller.
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                # Suppress close errors to avoid masking the original exception
                pass
        return None


if __name__ == "__main__":
    try:
        with DatabaseManager() as db:
            columns, rows = db.execute_query("""
                SELECT FirstName, LastName, Company
                FROM Customer
                WHERE Company IS NOT NULL
                LIMIT 5;
            """)

            # cursor.description is a sequence of 7-tuples per column; index 0 is the name.
            # We pass only the column names to DataFrame so pandas uses them as headers,
            # and rows as the data. Any SQL NULL in the result will appear as NaN in the DataFrame.
            column_names = [col[0] for col in columns]
            df = pd.DataFrame(rows, columns=column_names)
            print(df)
    except DatabaseError as e:
        print(f"Database error: {e}")
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")