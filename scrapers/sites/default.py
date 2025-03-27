"""
This module provides a web scraper implementation for generic websites.

The `DefaultScraper` class extends the `BaseScraper` and offers capabilities for automated
web scraping tasks using Playwright. It includes handling cookies, loading additional 
comments, and extracting HTML content from specified containers on web pages.
"""

import logging
from typing import Optional

from playwright.sync_api import Playwright

from ..base import BaseScraper
from ..utils import browser_context, click_button_until_gone

logger = logging.getLogger(__name__)


class DefaultScraper(BaseScraper):
    """
    Default scraper implementation for generic websites.

    This scraper automates common tasks required during web scraping, such as:
    - Handling cookie consent dialogs.
    - Clicking "Load More" buttons to expose additional content.
    - Extracting HTML content for further processing.
    """

    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        """
        Perform web scraping on the provided URL using the Playwright browser automation framework.

        Args:
            playwright (Playwright): The Playwright instance used for browser automation.
            url (str): The target URL of the website to scrape.
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to False.
            max_pages (Optional[int], optional): Reserved for future iteration limit on pagination. Defaults to None.

        Returns:
            str: The combined HTML content extracted from the target website.

        Raises:
            Exception: Reraises any exception encountered during web scraping.
        """
        logger.info(f'Starting web scraping for URL: {url}')

        try:
            with browser_context(playwright, headless) as page:
                playwright.selectors.set_test_id_attribute('data-testid')
                page.goto(url)
                html_content = []

                # Handle cookie consent
                if self.config.accept_cookies_selector:
                    logger.info('Accepting cookies')
                    click_button_until_gone(page, self.config.accept_cookies_selector)

                # Click to expose comments
                if self.config.expose_initial_comments_selector:
                    logger.info('Exposing initial comments')
                    click_button_until_gone(page, self.config.expose_initial_comments_selector)

                # Click all configured "more" buttons
                if self.config.more_comments_selectors:
                    logger.info('Loading more comments')
                    for selector in self.config.more_comments_selectors:
                        click_button_until_gone(page, selector)

                # Get initial page content
                html_content.append(self.config.get_container_html(page))

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise

        logger.info('Completed web scraping')
        return ''.join(html_content)
