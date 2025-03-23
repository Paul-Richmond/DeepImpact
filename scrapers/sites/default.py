import logging
from typing import Optional

from playwright.sync_api import Playwright

from ..base import BaseScraper
from ..utils import browser_context, click_button_until_gone

logger = logging.getLogger(__name__)


class DefaultScraper(BaseScraper):
    """Default scraper implementation for generic websites"""

    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        logger.info(f'Starting web scraping for URL: {url}')

        try:
            with browser_context(playwright, headless) as page:
                page.goto(url)
                html_content = []

                # Handle cookie consent
                if self.config.accept_cookies_selector:
                    logger.info('Accepting cookies')
                    click_button_until_gone(page, self.config.accept_cookies_selector)

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