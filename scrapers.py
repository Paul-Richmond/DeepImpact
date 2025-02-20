import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Union
from dataclasses import dataclass
from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError
from contextlib import contextmanager
import yaml

# # Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@dataclass
class SelectorConfig:
    """Configuration for a single selector with various possible types"""
    selector_type: str  # 'label', 'role', 'text', 'test_id', 'id'
    value: Union[str, Pattern]  # Can be either string or compiled regex pattern
    role_name: Optional[str] = None  # Only used when selector_type is 'role'
    select_option: Optional[str] = None


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    # site_code: str
    accept_cookies_selector: Optional[SelectorConfig] = None
    reorder_comments_first: Optional[bool] = None
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


def convert_selector_config(selector_dict: Dict[str, Any]) -> SelectorConfig:
    """
    Convert a dictionary to a SelectorConfig object

    Args:
        selector_dict: Dictionary containing selector configuration

    Returns:
        SelectorConfig object
    """
    if 'role' in selector_dict:
        return SelectorConfig(
            selector_type='role',
            value=selector_dict['role'],
            role_name=selector_dict.get('name')
        )
    elif 'text' in selector_dict:
        return SelectorConfig(
            selector_type='text',
            value=selector_dict['text']
        )
    elif 'id' in selector_dict:
        return SelectorConfig(
            selector_type='id',
            value=selector_dict['id']
        )
    elif 'label' in selector_dict:
        return SelectorConfig(
            selector_type='label',
            value=selector_dict['label']
        )
    elif 'test_id' in selector_dict:
        return SelectorConfig(
            selector_type='test_id',
            value=selector_dict['test_id'],
            select_option=selector_dict.get('select_option')
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
        'accept_cookies_selector': (
            convert_selector_config(config['accept_cookies_selector'])
            if 'accept_cookies_selector' in config else None
        ),
        'comments_order_selector': (
            convert_selector_config(config['comments_order_selector'])
            if 'comments_order_selector' in config else None
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


def click_button(page, selector: SelectorConfig, timeout: int = 10000) -> None:
    """Click a button once"""
    try:
        button = get_locator(page, selector)
        if selector.select_option:
            button.select_option(selector.select_option)
        button.first.click(timeout=timeout)
        logger.debug(f"Successfully clicked button: {selector}")
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
            if config.comments_order_selector is True:
                # Reorder first
                logger.info('Reordering comments')
                click_button(page, config.comments_order_selector)
                # Then expose initial comments
                if config.expose_initial_comments_selector:
                    logger.info('Exposing initial comments')
                    click_button_until_gone(page, config.expose_initial_comments_selector)
            else:
                # Expose initial comments first
                if config.expose_initial_comments_selector:
                    logger.info('Exposing initial comments')
                    click_button_until_gone(page, config.expose_initial_comments_selector)
                # Then reorder
                logger.info('Reordering comments')
                click_button(page, config.comments_order_selector)

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
