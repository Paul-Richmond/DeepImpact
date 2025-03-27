"""
This module provides tools for managing and interacting with a SQLite database
designed for web archiving purposes. The `WebArchiveDB` class simplifies database
operations specific to web scraping, such as storing, updating, and retrieving
metadata about scraped website content.

Key Features:
- Initialization and configuration of a SQLite database file.
- Transaction management using a context manager.
- Safe and efficient handling of SQL queries with parameterization.
- Automatic setup of database tables and indexing to optimize performance.
- Custom data type handling for seamless conversion of dates.

Usage Example:
    >>> db = WebArchiveDB()
    >>> with db:
    >>>     record_id = db.add_to_database({
    >>>         "site": "example.com",
    >>>         "url": "https://example.com",
    >>>         "target": "example_page",
    >>>         "scraping_config": "{}"
    >>>     })
    >>>     print(f"Record added with ID: {record_id}")
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class WebArchiveDB:
    """A class for managing a SQLite database tailored to web archiving.
    
    The `WebArchiveDB` class handles operations such as creating database tables,
    inserting records, updating scraping metadata, and retrieving information
    about archived websites. It provides an object-oriented interface for interacting
    with the database while handling common tasks such as transaction management,
    date conversions, and table creation.
    
    Key Features:
    - Initialize and configure a SQLite database automatically.
    - Sanitize table names to prevent SQL injection risks.
    - Provide developer-friendly utilities for handling dates and SQL queries.
    - Offer robust error handling with detailed logging.
    - Support a context manager interface for handling the lifecycle of database connections.
    
    Example Usage:
        db = WebArchiveDB("web_data.db")
    
        # Inserting a new record
        with db:
            db.add_to_database({
                "site": "example.com",
                "url": "https://example.com",
                "target": "homepage",
                "scraping_config": '{"depth": 2, "type": "full"}'
            })
    
        # Fetching a record by URL
        with db:
            record = db.get_by_url("https://example.com")
            print(record["site"])  # Outputs: example.com
    """

    def __init__(self,
                 db_path: Union[str, Path] = "db/web_archive.db",
                 db_table_name: str = "web_archive"
                 ) -> None:
        """Initialize the WebArchiveDB.

        Args:
            db_path: Path to the SQLite database file
            db_table_name: Name of the table to store web archive data
        """
        self.db_path = Path(db_path)
        self.db_table_name = self._validate_table_name(db_table_name)
        self.name = Path(db_path).stem

        # Register adapters and converters
        sqlite3.register_adapter(date, self._adapt_date_iso)
        sqlite3.register_converter("DATE", self._convert_date_iso)

        self._initialize_connection()
        self.setup_database()

    def _initialize_connection(self) -> None:
        """Establish a connection to the SQLite database.
        
        This method sets up a connection to the SQLite database file specified in `db_path`.
        It enables autocommit mode, configures the connection to parse declared types,
        and sets the row factory to `sqlite3.Row` for dictionary-style access to query results.
        
        The method also initializes a cursor for executing database operations.
        
        Raises:
            sqlite3.Error: If the connection to the database fails.
        """
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                isolation_level=None  # Enable autocommit mode
            )
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise

    @staticmethod
    def _validate_table_name(name: str) -> str:
        """Validate and sanitize the table name to prevent SQL injection.

        Args:
            name: The table name to validate

        Returns:
            str: The validated table name

        Raises:
            ValueError: If the table name contains invalid characters
        """
        if not all(c.isalnum() or c == '_' for c in name):
            raise ValueError("Table name must contain only alphanumeric characters and underscores")
        if not name[0].isalpha():
            raise ValueError("Table name must start with a letter")
        return name

    @staticmethod
    def _adapt_date_iso(val: date) -> str:
        """Adapt `datetime.date` to ISO 8601 date string."""
        return val.isoformat()

    @staticmethod
    def _convert_date_iso(val: bytes) -> date:
        """Convert ISO 8601 date string to datetime.date."""
        return datetime.strptime(val.decode(), "%Y-%m-%d").date()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            self.cursor.execute("BEGIN")
            yield
            self.cursor.execute("COMMIT")
        except Exception as e:
            self.cursor.execute("ROLLBACK")
            logger.error(f"Transaction failed, rolling back: {e}")
            raise

    def setup_database(self) -> bool:
        """Create the necessary table if it doesn't exist."""
        try:
            with self.transaction():
                self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        site TEXT NOT NULL,
                        url TEXT UNIQUE NOT NULL,
                        target TEXT NOT NULL,
                        scraping_config TEXT NOT NULL,
                        last_scraped DATE,
                        times_scraped INTEGER DEFAULT 0,
                        html_file TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for better query performance
                self.cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self.db_table_name}_url ON {self.db_table_name}(url)")
                self.cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self.db_table_name}_site ON {self.db_table_name}(site)")

            logger.info(f"Database table {self.db_table_name} initialized successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to setup database: {e}")
            raise

    def add_scrape_file_and_time(self, filename: str, url_id: int) -> bool:
        """Update the scraping metadata (file name and timestamp) for a specific URL.
        
        This method updates the following fields in the database:
        - `last_scraped`: The date when the URL was last scraped.
        - `times_scraped`: Increments the count of how many times the URL has been scraped.
        - `html_file`: The name of the file where the scraped content is saved.
        
        Args:
            filename (str): Name of the HTML file that contains the scraped content.
            url_id (int): The unique ID of the URL record to update.
        
        Returns:
            bool: True if the update was successful, otherwise False if no matching record was found.
        
        Raises:
            sqlite3.Error: If any database-related error occurs during the operation.
        """
        try:
            with self.transaction():
                self.cursor.execute(f"""
                    UPDATE {self.db_table_name} 
                    SET last_scraped = ?, 
                        times_scraped = times_scraped + 1, 
                        html_file = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (date.today(), filename, url_id))

                if self.cursor.rowcount == 0:
                    logger.warning(f"No record found for URL ID {url_id}")
                    return False

            logger.debug(f"Successfully updated scrape info for URL ID {url_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to update scrape file and time: {e}")
            raise

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[sqlite3.Row]:
        """Execute a SQL query with optional parameters and return the results.
        
        This method runs a given SQL query against the database and fetches all matching
        rows. It uses parameterized queries to prevent SQL injection attacks.
        
        Args:
            sql (str): The SQL query string to execute.
            params (Optional[tuple]): A tuple of parameters to safely substitute into
                                      the query. Defaults to None.
        
        Returns:
            List[sqlite3.Row]: A list of results represented as sqlite3.Row objects.
                               Each row can be accessed like a dictionary.
        
        Raises:
            sqlite3.Error: If an error occurs while executing the query.
        """
        try:
            with self.transaction():
                self.cursor.execute(sql, params or ())
                return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def add_to_database(self, data: Dict[str, Any]) -> int:
        """Add a new record to the database.

        Args:
            data: Dictionary containing column names and values to insert

        Returns:
            int: ID of the newly inserted record

        Raises:
            ValueError: If required fields are missing
            sqlite3.Error: If database operation fails
        """
        required_fields = {'site', 'url', 'target', 'scraping_config'}
        if not required_fields.issubset(data.keys()):
            missing = required_fields - set(data.keys())
            raise ValueError(f"Missing required fields: {missing}")

        try:
            with self.transaction():
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = tuple(data.values())

                self.cursor.execute(
                    f"INSERT INTO {self.db_table_name} ({columns}) VALUES ({placeholders})",
                    values
                )

                new_id = self.cursor.lastrowid
                logger.info(f"Successfully added new record with ID {new_id}")
                return new_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error while adding record: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Database error while adding record: {e}")
            raise

    def get_by_url(self, url: str) -> Optional[sqlite3.Row]:
        """Retrieve a database record associated with a specific URL.
        
        This method searches for a single record in the database with a `url` value
        matching the input and returns the corresponding row.
        
        Args:
            url (str): The URL to search for within the database.
        
        Returns:
            Optional[sqlite3.Row]: A row object representing the record if found,
                                   or None if no matching record exists.
        
        Raises:
            sqlite3.Error: If an error occurs while executing the query.
        """
        try:
            self.cursor.execute(
                f"SELECT * FROM {self.db_table_name} WHERE url = ?",
                (url,)
            )
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve record by URL: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()
