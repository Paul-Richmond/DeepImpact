"""
Base scraper module for web scraping.

This module defines a base class `BaseScraper` that provides a foundation
for implementing specific website scrapers. Scrapers inheriting from this class
must implement the `scrape` abstract method for performing website scraping.

Key Features:
- Provides a consistent interface for scrapers to define scraping behavior.
- Offers a helper method `write_to_file` to handle file-writing operations.
- Uses `SiteConfig` for managing website-specific configurations.

Classes:
- BaseScraper: Abstract base class for specific website scrapers.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from playwright.sync_api import Playwright

from .config import SiteConfig

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for website-specific scrapers.
    
    This class is designed to be inherited by scraper classes that target specific
    websites. It defines a common interface for web scraping and includes methods
    for writing scraped content to files. Implementing classes must provide their
    own implementation of the `scrape` method.
    
    Attributes:
        config (SiteConfig): Configuration object containing website-specific settings.
    """

    def __init__(self, config: SiteConfig):
        """
        Initialize the base scraper with a specific site configuration.
        
        Args:
            config (SiteConfig): An object containing website-specific configuration
                data, such as selectors and scraping rules.
        """
        self.config = config

    @abstractmethod
    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        """
        Abstract method to perform web scraping for a specific website.
        
        This method must be implemented by all subclasses to define their
        scraping logic.
        
        Args:
            playwright (Playwright): The Playwright instance to interact with web pages.
            url (str): The URL of the webpage to scrape.
            headless (bool, optional): If True, run the scraper in headless mode.
                Defaults to False.
            max_pages (Optional[int], optional): The maximum number of pages to scrape.
                Defaults to None, meaning no limit.
        
        Returns:
            str: The scraped content as a string.
        
        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        pass

    def write_to_file(self, content: str, filename: str) -> None:
        """
        Write scraped content to a file.
        
        This method writes the provided content to the specified file, ensuring that
        all necessary directories are created if they do not already exist.
        
        Args:
            content (str): The string content to write to the file.
            filename (str): The path to the file where the content will be saved.
        
        Raises:
            PermissionError: If the program does not have permission to write to the file.
            OSError: If any other file-related error occurs.
        
        Logs:
            Info: When the file is successfully written.
            Error: When there is an issue writing the file.
        """
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
