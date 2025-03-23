from abc import ABC, abstractmethod
import logging
import re
import yaml
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Union

from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


#############
# Data Models
#############

@dataclass
class SelectorConfig:
    """Configuration for a single selector with various possible types"""
    selector_type: str  # 'label', 'role', 'text', 'test_id', 'id', 'iframe'
    value: Union[str, Pattern]  # Can be either string or compiled regex pattern
    role_name: Optional[Union[str, Pattern]] = None  # Used when selector_type is 'role'
    select_option: Optional[str] = None


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    # site_code: str
    switch_to_frame_selector: Optional[SelectorConfig] = None
    accept_cookies_selector: Optional[SelectorConfig] = None
    comments_order_selectors: Optional[List[SelectorConfig]] = None
    expose_initial_comments_selector: Optional[SelectorConfig] = None
    page_buttons_selector: Optional[SelectorConfig] = None
    more_comments_selectors: Optional[List[SelectorConfig]] = None
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


###########################
# Configuration Utilities
###########################

def convert_selector_config(selector_dict: Dict[str, Any]) -> SelectorConfig:
    """
    Convert a dictionary to a SelectorConfig object

    Args:
        selector_dict: Dictionary containing selector configuration

    Returns:
        SelectorConfig object
    """
    if 'iframe' in selector_dict:
        return SelectorConfig(
            selector_type='iframe',
            value=selector_dict['iframe']
        )
    elif 'role' in selector_dict:
        return SelectorConfig(
            selector_type='role',
            value=selector_dict['role'],
            role_name=selector_dict.get('name')
        )
    elif 'label' in selector_dict:
        return SelectorConfig(
            selector_type='label',
            value=selector_dict['label']
        )
    elif 'placeholder' in selector_dict:
        return SelectorConfig(
            selector_type='placeholder',
            value=selector_dict['placeholder']
        )
    elif 'text' in selector_dict:
        return SelectorConfig(
            selector_type='text',
            value=selector_dict['text']
        )
    elif 'all_text' in selector_dict:
        return SelectorConfig(
            selector_type='all_text',
            value=selector_dict['all_text']
        )
    elif 'title' in selector_dict:
        return SelectorConfig(
            selector_type='title',
            value=selector_dict['title']
        )
    elif 'test_id' in selector_dict:
        return SelectorConfig(
            selector_type='test_id',
            value=selector_dict['test_id'],
            select_option=selector_dict.get('select_option')
        )
    elif 'id' in selector_dict:
        return SelectorConfig(
            selector_type='id',
            value=selector_dict['id']
        )
    else:
        raise ValueError(f"Unknown selector type in configuration: {selector_dict}")


def load_site_config(yaml_path: str, config_name: str) -> SiteConfig:
    """
    Load YAML file and convert to SiteConfig object for specified configuration

    Args:
        yaml_path: Path to YAML configuration file
        config_name: Name of the configuration to load (e.g., 'dm_cfg1')

    Returns:
        SiteConfig object for the specified configuration

    Raises:
        ValueError: If the specified configuration name is not found in the YAML file
    """
    # Add a constructor to yaml.Loader which will convert the YAML tag
    # !!python/object/apply:re._compile
    # into a re.compile object
    yaml.Loader.add_constructor('!!python/object/apply:re._compile',
                                lambda loader, node: re.compile(*loader.construct_sequence(node)))
    with open(yaml_path, 'r') as file:
        yaml_config = yaml.load(file, Loader=yaml.Loader)

    if config_name not in yaml_config:
        raise ValueError(f"Configuration '{config_name}' not found in YAML file")

    config = yaml_config[config_name]

    # Convert each selector configuration
    site_config_dict = {
        'switch_to_frame_selector': (
            convert_selector_config(config['switch_to_frame_selector'])
            if 'switch_to_frame_selector' in config else None
        ),
        'accept_cookies_selector': (
            convert_selector_config(config['accept_cookies_selector'])
            if 'accept_cookies_selector' in config else None
        ),
        'comments_order_selectors': (
            [convert_selector_config(selector) for selector in config['comments_order_selectors']]
            if 'comments_order_selectors' in config else None
        ),
        'expose_initial_comments_selector': (
            convert_selector_config(config['expose_initial_comments_selector'])
            if 'expose_initial_comments_selector' in config else None
        ),
        'page_buttons_selector': (
            convert_selector_config(config['page_buttons_selector'])
            if 'page_buttons_selector' in config else None
        ),
        'more_comments_selectors': (
            [convert_selector_config(selector) for selector in config['more_comments_selectors']]
            if 'more_comments_selectors' in config else None
        ),
        'comments_container_selector': (
            convert_selector_config(config['comments_container_selector'])
            if 'comments_container_selector' in config else None
        )
    }

    return SiteConfig(**site_config_dict)


###########################
# Browser Interaction Utils
###########################

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
        case 'test_id':
            return page.get_by_test_id(selector.value)
        case 'id':
            return page.locator(selector.value)
        case _:
            raise ValueError(f"Unsupported selector type: {selector.selector_type}")


def get_iframe(page, selector: SelectorConfig):
    """Get an iframe based on the selector configuration"""
    match selector.selector_type:
        case 'iframe':
            return page.frame_locator(f"iframe[title=\"{selector.value}\"]")
        case _:
            raise ValueError(f"Unsupported selector type: {selector.selector_type}")


def click_button_until_gone(page, selector: SelectorConfig, timeout: int = 5000, max_clicks: int = 200) -> None:
    """Click a button repeatedly until it's no longer available or max_clicks is reached"""
    try:
        click_count = 0
        while click_count < max_clicks:
            try:
                button = get_locator(page, selector)
                # button.scroll_into_view_if_needed()
                button.first.click(timeout=timeout)
                click_count += 1
                logger.debug(f"Successfully clicked button: {selector} (click {click_count}/{max_clicks})")
            except PlaywrightTimeoutError:
                logger.debug(f"Button no longer available: {selector}")
                break
        if click_count >= max_clicks:
            logger.info(f"Reached maximum number of clicks ({max_clicks}) for selector: {selector}")
            logger.warning(f"All comments may not have been loaded for: {selector}")
    except Exception as e:
        logger.error(f"Error while clicking button: {e}")
        raise


def click_button(page, selector: SelectorConfig, timeout: int = 5000) -> None:
    try:
        button = get_locator(page, selector)
        button.scroll_into_view_if_needed()
        button.first.click(timeout=timeout)
        logger.debug(f"Successfully clicked button: {selector}")
    except PlaywrightTimeoutError:
        logger.debug(f"Button no longer available: {selector}")
    except Exception as e:
        logger.error(f"Error while clicking button: {e}")
        raise


def write_raw_html_to_file(raw_html: str, filename: str) -> Optional[str]:
    """
    Write HTML content to a file, creating directories if they don't exist.

    Args:
        raw_html (str): The HTML content to write
        filename (str): The target filename/path

    Returns:
        Optional[str]: None if successful, error message if failed
    """
    try:
        # Convert filename to Path object for easier handling
        file_path = Path(filename)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(raw_html)

        logger.info(f"Raw HTML content has been written to {filename}")
        return None

    except PermissionError:
        logger.error(f"Permission denied when trying to write to {filename}")
        raise
    except OSError as e:
        logger.error(f"Error writing file: {str(e)}")
        raise


###########################
# Scraper Classes
###########################

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
        write_raw_html_to_file(content, filename)


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


class GuardianScraper(BaseScraper):
    """Scraper implementation for The Guardian website"""

    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        logger.info(f'Starting Guardian web scraping for URL: {url}')

        try:
            with browser_context(playwright, headless) as page:
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


class ScraperFactory:
    """Factory class to create appropriate scrapers based on website"""

    @staticmethod
    def create_scraper(site_type: str, config: SiteConfig) -> BaseScraper:
        """
        Create and return a scraper for the specified site type

        Args:
            site_type: Type of website (e.g., 'The Guardian', 'Daily Mail', 'BBC')
            config: Site configuration

        Returns:
            BaseScraper: An instance of the appropriate scraper

        Raises:
            ValueError: If the site type is not supported
        """
        scrapers = {
            'The Guardian': GuardianScraper,
            'Daily Mail': DefaultScraper,
            'BBC': DefaultScraper,
            # Add more scrapers here as they are implemented
        }

        if site_type not in scrapers:
            logger.warning(f"Unknown site type '{site_type}'. Using default scraper.")
            return DefaultScraper(config)

        return scrapers[site_type](config)


###########################
# Main Function
###########################

def scrape_site_html(
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
        str: Combined HTML content of all scraped comments
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
