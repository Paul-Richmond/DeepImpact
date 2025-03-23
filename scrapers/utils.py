import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError

from .config import SelectorConfig

logger = logging.getLogger(__name__)


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
