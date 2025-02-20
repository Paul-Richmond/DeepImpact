import yaml
import json
from typing import Dict, Any, Optional, List, Union
import sqlite3
from datetime import date, datetime
from pathlib import Path
import logging
from contextlib import contextmanager


# The cls_loader and get_loader functions are slight modifications
# to those found in https://matthewpburruss.com/post/yaml/
def cls_loader(loader, node):
    """A loader for classes."""
    params = loader.construct_mapping(node)  # get node mappings
    module = __import__(params["module"], fromlist=[params["name"]])  # load Python module
    return getattr(module, params["name"])  # get class from module


def get_loader():
    """Return a yaml loader."""
    loader = yaml.SafeLoader
    loader.add_constructor("!Cls", cls_loader)
    return loader


def load_config_yaml(filepath):
    with open(filepath, 'r') as f:
        parameters = yaml.load(f, Loader=get_loader())
    return parameters


def export_output(filepath, url, data):
    """Export the url and data to a json file."""
    data_as_dict = data.to_dict()
    data_as_dict.update({"url": url})
    with open(filepath, 'w') as f:
        json.dump(data_as_dict, f)


class WebArchiveDB:
    """A class to manage a SQLite database for web archive operations.

    This class provides functionality to store and manage web scraping data,
    including URLs, scraping configurations, and archived HTML files.
    """

    def __init__(
            self,
            db_path: Union[str, Path] = "db/web_archive.db",
            db_table_name: str = "web_archive",
            log_level: int = logging.INFO
    ):
        """Initialize the WebArchiveDB.

        Args:
            db_path: Path to the SQLite database file
            db_table_name: Name of the table to store web archive data
            log_level: Logging level for the database operations
        """
        self.db_path = Path(db_path)
        self.db_table_name = self._validate_table_name(db_table_name)
        self.name = Path(db_path).stem

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Register adapters and converters
        sqlite3.register_adapter(date, self._adapt_date_iso)
        sqlite3.register_converter("DATE", self._convert_date_iso)

        self._initialize_connection()
        self.setup_database()

    def _initialize_connection(self) -> None:
        """Initialize the database connection with proper settings."""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                isolation_level=None  # Enable autocommit mode
            )
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
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
            self.logger.error(f"Transaction failed, rolling back: {e}")
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

            self.logger.info(f"Database table {self.db_table_name} initialized successfully")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to setup database: {e}")
            raise

    def add_scrape_file_and_time(self, filename: str, url_id: int) -> bool:
        """Update the scrape file and timestamp for a given URL.

        Args:
            filename: Name of the HTML file where the scraped content is stored
            url_id: ID of the URL record to update

        Returns:
            bool: True if update was successful
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
                    self.logger.warning(f"No record found for URL ID {url_id}")
                    return False

            self.logger.debug(f"Successfully updated scrape info for URL ID {url_id}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update scrape file and time: {e}")
            raise

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[sqlite3.Row]:
        """Execute a SQL query with parameters.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of query results as Row objects
        """
        try:
            with self.transaction():
                self.cursor.execute(sql, params or ())
                return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {e}")
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
                self.logger.info(f"Successfully added new record with ID {new_id}")
                return new_id

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error while adding record: {e}")
            raise
        except sqlite3.Error as e:
            self.logger.error(f"Database error while adding record: {e}")
            raise

    def get_by_url(self, url: str) -> Optional[sqlite3.Row]:
        """Retrieve a record by its URL.

        Args:
            url: URL to search for

        Returns:
            Optional[sqlite3.Row]: Record if found, None otherwise
        """
        try:
            self.cursor.execute(
                f"SELECT * FROM {self.db_table_name} WHERE url = ?",
                (url,)
            )
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve record by URL: {e}")
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
