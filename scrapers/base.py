import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from playwright.sync_api import Playwright

from .config import SiteConfig

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for website-specific scrapers"""

    def __init__(self, config: SiteConfig):
        self.config = config

    @abstractmethod
    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        """Main scraping method to be implemented by each website scraper"""
        pass

    def write_to_file(self, content: str, filename: str) -> None:
        """Helper method to write scraped content to a file"""
        try:
            # Convert filename to Path object for easier handling
            file_path = Path(filename)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Raw HTML content has been written to {filename}")

        except PermissionError:
            logger.error(f"Permission denied when trying to write to {filename}")
            raise
        except OSError as e:
            logger.error(f"Error writing file: {str(e)}")
            raise
