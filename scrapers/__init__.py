"""
This module provides the functionality to scrape html containing user comments from different news sites.

It includes:
- A setup for logging.
- A function `scrape_comments_html` that acts as the main entry point for scraping comments.
- Dependencies for scraping: a Playwright instance, configuration loading, and scraper factories.
"""

import logging
from typing import Optional

from playwright.sync_api import Playwright

from .base import BaseScraper
from .config import SiteConfig, SelectorConfig, load_site_config
from .factory import ScraperFactory
from .logger_setup import setup_logging

setup_logging(log_level=logging.INFO, log_file=None)
logger = logging.getLogger(__name__)


def scrape_comments_html(
        playwright: Playwright,
        url: str,
        site_type: str,
        config_path: str,
        config_name: str,
        output_path: Optional[str] = None,
        headless: bool = False,
        max_pages: Optional[int] = None
) -> str:
    """
    Main function to scrape comments from supported news sites

    Args:
        playwright: Playwright instance
        url: Target URL to scrape
        site_type: Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')
        config_path: Path to the YAML configuration file
        config_name: Name of the configuration to use
        output_path: Optional path to save the HTML output
        headless: Whether to run browser in headless mode
        max_pages: Maximum number of pages to scrape (None for all pages)

    Returns:
        str: HTML content which includes all scraped comments and comment data such as usernames, timestamps, likes, etc.
    """
    # Load the configuration
    config = load_site_config(config_path, config_name)

    # Create the appropriate scraper
    scraper = ScraperFactory.create_scraper(site_type, config)

    # Perform the scraping
    html_content = scraper.scrape(playwright, url, headless, max_pages)

    # Write to file if output path is provided
    if output_path:
        scraper.write_to_file(html_content, output_path)

    return html_content
