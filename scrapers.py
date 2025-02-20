import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SelectorConfig:
    """Configuration for a single selector with various possible types"""
    selector_type: str  # 'label', 'role', 'text', 'test_id', 'id'
    value: str
    role_name: Optional[str] = None  # Only used when selector_type is 'role'


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    site_code: str
    accept_cookies_selector: Optional[SelectorConfig] = None
    comments_order_selector: Optional[SelectorConfig] = None
    expose_initial_comments_selector: Optional[SelectorConfig] = None
    page_buttons_selector: Optional[SelectorConfig] = None
    more_comments_selectors: List[SelectorConfig] = None
    comments_container_selector: SelectorConfig = None

    def get_container_html(self, page) -> str:
        """Get the HTML content of the comments container"""
        try:
            match self.comments_container_selector.selector_type:
                case 'test_id':
                    return page.get_by_test_id(self.comments_container_selector.value).inner_html()
                case 'label':
                    return page.get_by_label(self.comments_container_selector.value).inner_html()
                case 'id':
                    return page.locator(self.comments_container_selector.value).inner_html()
                case _:
                    raise ValueError(f"Unsupported selector type: {self.comments_container_selector.selector_type}")
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout while getting container HTML: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting container HTML: {e}")
            raise


@contextmanager
def browser_context(playwright: Playwright, headless: bool = False):
    """Context manager for browser handling"""
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()
        browser.close()


def get_locator(page, selector: SelectorConfig):
    """Get a locator based on the selector configuration"""
    match selector.selector_type:
        case 'label':
            return page.get_by_label(selector.value)
        case 'role':
            return page.get_by_role(selector.value, name=selector.role_name)
        case 'text':
            return page.get_by_text(selector.value)
        case _:
            raise ValueError(f"Unsupported selector type: {selector.selector_type}")


def click_button_until_gone(page, selector: SelectorConfig, timeout: int = 10000) -> None:
    """Click a button repeatedly until it's no longer available"""
    try:
        while True:
            try:
                button = get_locator(page, selector)
                button.first.click(timeout=timeout)
                logger.debug(f"Successfully clicked button: {selector}")
            except PlaywrightTimeoutError:
                logger.debug(f"Button no longer available: {selector}")
                break
    except Exception as e:
        logger.error(f"Error while clicking button: {e}")
        raise


def scrape_comments(
        playwright: Playwright,
        url: str,
        config: SiteConfig,
        headless: bool = False,
        max_pages: Optional[int] = None
) -> str:
    """
    Main function to scrape comments from supported news sites

    Args:
        playwright: Playwright instance
        url: Target URL to scrape
        config: Site configuration
        headless: Whether to run browser in headless mode
        max_pages: Maximum number of pages to scrape (None for all pages)

    Returns:
        str: Combined HTML content of all scraped comments
    """
    logger.info(f'Starting web scraping for URL: {url}')

    try:
        with browser_context(playwright, headless) as page:
            page.goto(url)
            html_content = []

            # Handle cookie consent
            if config.accept_cookies_selector:
                logger.info('Accepting cookies')
                click_button_until_gone(page, config.accept_cookies_selector)

            # Expose initial comments
            if config.expose_initial_comments_selector:
                logger.info('Exposing initial comments')
                click_button_until_gone(page, config.expose_initial_comments_selector)

            # Click all configured "more" buttons
            if config.more_comments_selectors:
                logger.info('Loading more comments')
                for selector in config.more_comments_selectors:
                    click_button_until_gone(page, selector)

            # Get initial page content
            html_content.append(config.get_container_html(page))

            # Handle pagination
            if config.page_buttons_selector:
                logger.info('Processing pagination')
                page_num = 2
                while max_pages is None or page_num <= max_pages:
                    try:
                        logger.info(f'Accessing page {page_num}')
                        page.locator('li').filter(
                            has_text=re.compile(fr"^{page_num}$")
                        ).click(timeout=10000)

                        # Load more comments on new page
                        if config.more_comments_selectors:
                            for selector in config.more_comments_selectors:
                                click_button_until_gone(page, selector)

                        html_content.append(config.get_container_html(page))
                        page_num += 1
                    except PlaywrightTimeoutError:
                        logger.info('Reached last page')
                        break

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise

    logger.info('Completed web scraping')
    return ''.join(html_content)
