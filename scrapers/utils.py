"""
Playwright Utilities Module

This module provides an organized collection of utility functions to simplify and enhance browser automation tasks using the Playwright Python library.

Key Features:
- Comprehensive browser and context management for Chromium-based automation.
- Easy-to-use utilities for interacting with web elements, including advanced selector handling.
- Functions for flexible button clicking with enhanced error handling and logging.
- Tools for HTML content extraction and saving to the local filesystem.
- Command-line interface for parsing scraper-specific arguments.

These utilities streamline common web scraping and automation workflows, with error handling, logging features, and configuration options for robust and efficient browser interactions.
"""

import argparse
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError, Page, FrameLocator, Locator

from .config import SelectorConfig

logger = logging.getLogger(__name__)


###########################
# Argument Parsing
###########################

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the scraper application.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Specify a database table")

    parser.add_argument(
        "--table", "-t",
        required=True,
        help="The name of the database table to use"
    )

    return parser.parse_args()


###########################
# Browser Interaction Utils
###########################

@contextmanager
def browser_context(playwright: Playwright, headless: bool = False) -> Generator[Page, None, None]:
    """
    Manages a browser context for a Chromium browser, allowing actions and interactions
    to be performed in a temporary, isolated session. The browser is launched via the
    Playwright library, and resources are cleaned up automatically when the context
    exits, ensuring no lingering processes or sessions.

    This function is intended to be used as a context manager and provides a safe
    and simplified way to handle browser lifecycle management.

    Args:
        playwright: An instance of the Playwright library used to launch the browser.
        headless: A boolean flag indicating whether to run the browser in headless mode (default is False).
    Yields:
        Page: a Playwright Page instance, representing the browser page within the created context.
    """
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()
        browser.close()


def get_locator(page: Page, selector: SelectorConfig) -> 'Locator':
    """
    Gets a locator for elements matching the provided selector configuration.

    Args:
        page (Page): A Playwright Page object where the selector will be located.
        selector (SelectorConfig): Configuration object specifying selector type and value.

    Returns:
        Locator: A Playwright Locator object resolved from the provided selector.

    Raises:
        ValueError: If the selector type is not supported.
    """

    match selector.selector_type:
        case 'role':
            return page.get_by_role(selector.value, name=selector.role_name)
        case 'label':
            return page.get_by_label(selector.value)
        case 'placeholder':
            return page.get_by_placeholder(selector.value)
        case 'text':
            return page.get_by_text(selector.value)
        case 'alt_text':
            return page.get_by_alt_text(selector.value)
        case 'title':
            return page.get_by_title(selector.value)
        case 'test_id':
            return page.get_by_test_id(selector.value)
        case 'id':
            return page.locator(selector.value)
        case _:
            raise ValueError(f"Unsupported selector type: {selector.selector_type}")


def get_iframe(page: Page, selector: SelectorConfig) -> 'FrameLocator':
    """
    Retrieves a FrameLocator for the specified iframe, using the given selector configuration.

    This function is designed to locate iframes on a web page based on the title attribute of the iframe,
    as specified in the SelectorConfig. If the selector type is not 'iframe', an error is raised.

    Args:
        page (Page): A Playwright Page object used to locate the iframe.
        selector (SelectorConfig): A configuration object containing the selector type and value.

    Returns:
        Locator: A Playwright FrameLocator object that matches the specified iframe selector.

    Raises:
        ValueError: If the selector type is not 'iframe'.
    """
    match selector.selector_type:
        case 'iframe':
            return page.frame_locator(f"iframe[title=\"{selector.value}\"]")
        case _:
            raise ValueError(f"Unsupported selector type: {selector.selector_type}")


def click_button_until_gone(page, selector: SelectorConfig, timeout: int = 5000, max_clicks: int = 200) -> None:
    """
    Click a button repeatedly until it is no longer available, or the maximum number of clicks is reached.

    This function looks for a button using the provided selector, clicks it repeatedly up to `max_clicks` times,
    and stops if the button is no longer available before reaching the maximum. It is useful for situations where
    multiple clicks are needed (e.g., loading more content) until the button disappears.

    Args:
        page (Page): A Playwright Page object where the button is located.
        selector (SelectorConfig): A configuration object specifying the type and identifier of the button to click.
        timeout (int, optional): Maximum time in milliseconds to wait for the button to become clickable each time. 
            Defaults to 5000 ms.
        max_clicks (int, optional): The maximum number of click attempts for the button. Defaults to 200.

    Raises:
        PlaywrightTimeoutError: If the button is not available within the specified timeout.
        Exception: For other unexpected errors during execution.

    Logs:
        - DEBUG: Logs every successful click and when the button becomes unavailable.
        - INFO: Logs when the maximum number of clicks is reached.
        - WARNING: Logs if the maximum clicks are reached but the desired action (e.g., loading more content) 
          might not have completed.
        - ERROR: Logs unexpected errors encountered during execution.
    """
    try:
        click_count = 0
        while click_count < max_clicks:
            try:
                button = get_locator(page, selector)
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
    """
    Click a button on the page using a specified selector.

    This function locates a button on the page based on the given selector configuration,
    scrolls the button into view if necessary, and clicks it. Logging is used to track
    the success or failure of the button-click action.

    Args:
        page (Page): A Playwright Page object where the button resides.
        selector (SelectorConfig): Configuration object specifying the selector type and value 
            for locating the button.
        timeout (int, optional): Maximum time in milliseconds to wait for the button to be 
            clickable. Defaults to 5000 ms.

    Raises:
        PlaywrightTimeoutError: If the button is not clickable within the specified timeout.
        Exception: If an unexpected error occurs during execution.

    Logs:
        - DEBUG: Logs successful clicks and when the button becomes unavailable.
        - ERROR: Logs unexpected errors encountered during execution.
    """
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
    Save raw HTML content to a specified file, ensuring its directory exists.

    This function writes the provided HTML content to a file with the given 
    filename and ensures that any parent directories are created if they do 
    not already exist. It handles errors such as missing permissions or I/O 
    issues, logging detailed messages for troubleshooting.

    Args:
        raw_html (str): The HTML content to be written to the file.
        filename (str): The complete path (including filename) where the HTML 
            content should be saved.

    Returns:
        Optional[str]: None if the operation completes successfully. If an error 
            occurs, an exception is raised after logging the error details. 
            Possible exceptions include PermissionError and OSError.

    Raises:
        PermissionError: If the process lacks permissions to write to the file.
        OSError: For other OS-related errors, such as issues with the filesystem.

    Logs:
        - INFO: Logs success when the file is written successfully.
        - ERROR: Logs details of any errors that prevent the file from being saved.
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
