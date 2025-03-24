import logging
from typing import Optional

from playwright.sync_api import Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..base import BaseScraper
from ..utils import browser_context, click_button_until_gone, get_iframe, click_button

logger = logging.getLogger(__name__)


class GuardianScraper(BaseScraper):
    """Scraper implementation for The Guardian website"""

    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        logger.info(f'Starting Guardian web scraping for URL: {url}')

        try:
            with browser_context(playwright, headless) as page:
                playwright.selectors.set_test_id_attribute('data-commercial-id')
                page.goto(url)
                html_content = []

                # Handle switch to frame which contain cookie consent button
                if self.config.switch_to_frame_selector:
                    iframe = get_iframe(page, self.config.switch_to_frame_selector)
                else:
                    iframe = None

                # Handle cookie consent
                if self.config.accept_cookies_selector:
                    logger.info('Accepting cookies')
                    if iframe:
                        click_button_until_gone(iframe, self.config.accept_cookies_selector)
                    else:
                        click_button_until_gone(page, self.config.accept_cookies_selector)

                # Guardian-specific comment navigation
                # page.get_by_role("heading", name=re.compile("Comments")).scroll_into_view_if_needed()
                if self.config.comments_order_selectors:
                    for selector in self.config.comments_order_selectors:
                        click_button(page, selector)

                # Handle pagination
                logger.info('Processing pagination')
                page_num = 1
                while max_pages is None or page_num <= max_pages:
                    try:
                        logger.info(f'Accessing page {page_num}')
                        page.get_by_role("button", name=str(page_num), exact=True).first.click(timeout=10000)

                        # Load more comments on new page
                        if self.config.more_comments_selectors:
                            for selector in self.config.more_comments_selectors:
                                click_button_until_gone(page, selector)

                        html_content.append(self.config.get_container_html(page))
                        page_num += 1
                    except PlaywrightTimeoutError:
                        logger.info('Reached last page')
                        break

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise

        logger.info('Completed web scraping')
        return ''.join(html_content)
